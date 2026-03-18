class TestRoleAccess:
    def _login(self, client, user):
        """Helper to log in a user in the test client."""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

    def test_staff_cannot_access_admin(self, client, staff_user):
        self._login(client, staff_user)
        resp = client.get("/admin/", follow_redirects=False)
        assert resp.status_code == 403

    def test_admin_can_access_admin(self, client, admin_user):
        self._login(client, admin_user)
        resp = client.get("/admin/")
        assert resp.status_code == 200

    def test_staff_cannot_access_dashboard(self, client, staff_user):
        self._login(client, staff_user)
        resp = client.get("/dashboard/", follow_redirects=False)
        assert resp.status_code == 403

    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/purchases/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]
