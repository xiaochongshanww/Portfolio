"""媒体库权限控制测试。

注意:app.media 包在模块级 import 时会触发 media/routes.py 的 @limiter.limit,
而 limiter 直到 create_app() 后才被赋值;因此这里所有对 permissions 的导入
都放在测试函数体内(此时 app fixture 已运行 create_app)。
"""

from app import db
from app.models import Media, MediaFolder

from .helpers import create_user


def _perms():
    from app.media.permissions import (
        can_delete_folder,
        can_delete_media,
        can_modify_folder,
        can_modify_media,
        can_view_folder,
        can_view_media,
        filter_media_by_permissions,
        get_folder_query_for_user,
        get_media_query_for_user,
    )

    return {
        "can_delete_folder": can_delete_folder,
        "can_delete_media": can_delete_media,
        "can_modify_folder": can_modify_folder,
        "can_modify_media": can_modify_media,
        "can_view_folder": can_view_folder,
        "can_view_media": can_view_media,
        "filter_media_by_permissions": filter_media_by_permissions,
        "get_folder_query_for_user": get_folder_query_for_user,
        "get_media_query_for_user": get_media_query_for_user,
    }


def _media(owner_id, visibility="private"):
    m = Media(
        filename="a.jpg",
        original_name="a.jpg",
        file_path="2025/a.jpg",
        file_size=100,
        mime_type="image/jpeg",
        media_type="image",
        owner_id=owner_id,
        visibility=visibility,
    )
    db.session.add(m)
    db.session.commit()
    return m


def _folder(owner_id, visibility="private"):
    f = MediaFolder(name="Folder", owner_id=owner_id, visibility=visibility)
    db.session.add(f)
    db.session.commit()
    return f


class TestMediaQueries:
    def test_admin_sees_all(self, app):
        u1 = create_user()
        u2 = create_user()
        _media(u1)
        _media(u2)
        assert _perms()["get_media_query_for_user"](u1, "admin").count() == 2

    def test_editor_sees_own_shared_public(self, app):
        me = create_user()
        other = create_user()
        _media(me, "private")
        _media(other, "shared")
        _media(other, "public")
        _media(other, "private")
        assert _perms()["get_media_query_for_user"](me, "editor").count() == 3

    def test_author_sees_own_public(self, app):
        me = create_user()
        other = create_user()
        _media(me, "private")
        _media(other, "public")
        _media(other, "shared")
        assert _perms()["get_media_query_for_user"](me, "author").count() == 2

    def test_unknown_role_sees_nothing(self, app):
        me = create_user()
        _media(me)
        assert _perms()["get_media_query_for_user"](me, "guest").count() == 0

    def test_folder_queries(self, app):
        me = create_user()
        other = create_user()
        _folder(me, "private")
        _folder(other, "public")
        _folder(other, "shared")
        g = _perms()["get_folder_query_for_user"]
        assert g(me, "editor").count() == 3  # own(me) + shared + public
        assert g(me, "author").count() == 2  # own(me) + public
        assert g(me, "guest").count() == 0
        assert g(me, "admin").count() == 3


class TestChecks:
    def test_can_view_media(self, app):
        p = _perms()
        me = create_user()
        other = create_user()
        pub = _media(other, "public")
        shared = _media(other, "shared")
        priv = _media(other, "private")
        mine = _media(me, "private")

        assert p["can_view_media"](pub, me, "author") is True
        assert p["can_view_media"](shared, me, "editor") is True
        assert p["can_view_media"](shared, me, "author") is False
        assert p["can_view_media"](priv, me, "author") is False
        assert p["can_view_media"](mine, me, "author") is True
        assert p["can_view_media"](priv, me, "admin") is True

    def test_can_modify_delete_media(self, app):
        p = _perms()
        me = create_user()
        other = create_user()
        theirs = _media(other, "public")
        mine = _media(me)
        assert p["can_modify_media"](theirs, me, "author") is False
        assert p["can_modify_media"](mine, me, "author") is True
        assert p["can_modify_media"](theirs, me, "admin") is True
        assert p["can_delete_media"](mine, me, "author") is True
        assert p["can_delete_media"](theirs, me, "author") is False
        assert p["can_delete_media"](theirs, me, "admin") is True

    def test_folder_checks(self, app):
        p = _perms()
        me = create_user()
        other = create_user()
        pub = _folder(other, "public")
        shared = _folder(other, "shared")
        priv = _folder(other, "private")
        mine = _folder(me)
        assert p["can_view_folder"](pub, me, "author") is True
        assert p["can_view_folder"](shared, me, "editor") is True
        assert p["can_view_folder"](shared, me, "author") is False
        assert p["can_view_folder"](priv, me, "author") is False
        assert p["can_view_folder"](mine, me, "author") is True
        assert p["can_view_folder"](priv, me, "admin") is True
        assert p["can_modify_folder"](mine, me, "author") is True
        assert p["can_modify_folder"](priv, me, "author") is False
        assert p["can_delete_folder"](mine, me, "author") is True
        assert p["can_delete_folder"](priv, me, "admin") is True
        assert p["can_delete_folder"](priv, me, "author") is False


class TestFilter:
    def test_filter_media_by_permissions(self, app):
        p = _perms()
        me = create_user()
        other = create_user()
        _media(me, "private")
        _media(other, "public")
        _media(other, "private")
        f = p["filter_media_by_permissions"]
        assert f(Media.query, me, "admin").count() == 3
        assert f(Media.query, me, "editor").count() == 2
        assert f(Media.query, me, "author").count() == 2
        assert f(Media.query, me, "guest").count() == 0
