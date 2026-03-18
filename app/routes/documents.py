from flask import Blueprint, abort, send_file, current_app
from flask_login import login_required, current_user
import io

from app.models.document import Document
from app.models.purchase import Purchase
from app.services.storage import get_storage_backend

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/<int:id>/download")
@login_required
def download(id):
    doc = Document.query.get_or_404(id)
    purchase = Purchase.query.get_or_404(doc.purchase_id)

    # Staff can only download their own purchase documents
    if current_user.role == "staff" and purchase.submitted_by_user_id != current_user.id:
        abort(403)

    storage = get_storage_backend()
    file_data, content_type = storage.get(doc.object_key)

    return send_file(
        io.BytesIO(file_data),
        mimetype=doc.content_type,
        as_attachment=True,
        download_name=doc.original_filename,
    )


@documents_bp.route("/<int:id>/view")
@login_required
def view(id):
    doc = Document.query.get_or_404(id)
    purchase = Purchase.query.get_or_404(doc.purchase_id)

    if current_user.role == "staff" and purchase.submitted_by_user_id != current_user.id:
        abort(403)

    storage = get_storage_backend()
    file_data, _ = storage.get(doc.object_key)

    return send_file(
        io.BytesIO(file_data),
        mimetype=doc.content_type,
        as_attachment=False,
        download_name=doc.original_filename,
    )
