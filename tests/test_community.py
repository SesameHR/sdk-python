import json

from conftest import Recorder, make_sdk

POSTS_PAYLOAD = {
    "data": [
        {
            "id": "post-1",
            "companyId": "company-1",
            "channel": {"channelId": "chan-1", "channelName": "General", "subscribed": True},
            "content": "Hello",
            "createdBy": {
                "id": "emp-2",
                "firstName": "Luis",
                "lastName": "Pérez",
                "imageProfileURL": None,
            },
            "createdAt": "2026-06-10T10:00:00",
            "updatedAt": "2026-06-10T10:00:00",
            "deletedAt": None,
            "commentsCount": 2,
            "reactions": [],
            "iRead": True,
            "image": None,
            "document": None,
            "openGraph": None,
        }
    ],
    "meta": {"currentPage": 1, "lastPage": 3, "total": 42, "perPage": 20},
}


def test_posts_defaults_to_authenticated_employee():
    recorder = Recorder(POSTS_PAYLOAD)
    sdk = make_sdk(recorder)

    page = sdk.community.posts()

    request = recorder.last
    assert request.url.path == "/private/community/v1/employee/employee-1/posts"
    assert request.url.params["orderBy"] == "createdAt desc"
    assert "channelId" not in request.url.params

    assert page.meta.current_page == 1
    assert page.meta.total == 42
    post = page.data[0]
    assert post.id == "post-1"
    assert post.channel.channel_name == "General"
    assert post.created_by.first_name == "Luis"
    assert post.i_read is True


def test_posts_with_channel_filter():
    recorder = Recorder(POSTS_PAYLOAD)
    sdk = make_sdk(recorder)

    sdk.community.posts(channel_id="chan-1", employee_id="emp-9")

    request = recorder.last
    assert request.url.path == "/private/community/v1/employee/emp-9/posts"
    assert request.url.params["channelId"] == "chan-1"


def test_create_post_text_only_sends_json():
    recorder = Recorder({"data": {"id": "post-9"}})
    sdk = make_sdk(recorder)

    result = sdk.community.create_post(channel_id="chan-1", content="Hola!")

    request = recorder.last
    assert request.url.path == "/private/community/v1/post"
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.content) == {"channel": "chan-1", "content": "Hola!"}
    assert result == {"id": "post-9"}


def test_create_post_with_file_sends_multipart():
    recorder = Recorder({"data": {"id": "post-10"}})
    sdk = make_sdk(recorder)

    result = sdk.community.create_post(
        channel_id="chan-1",
        content="with attachment",
        file=b"fake-image-bytes",
        file_name="photo.png",
    )

    request = recorder.last
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    assert b'name="channel"' in request.content
    assert b"chan-1" in request.content
    assert b'name="content"' in request.content
    assert b'filename="photo.png"' in request.content
    assert b"fake-image-bytes" in request.content
    assert result == {"id": "post-10"}


def test_create_post_with_url_link_sends_multipart():
    recorder = Recorder({"data": {"id": "post-11"}})
    sdk = make_sdk(recorder)

    sdk.community.create_post(channel_id="chan-1", url_link="https://example.com")

    request = recorder.last
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    assert b'name="urlLink"' in request.content
    assert b"https://example.com" in request.content
    # no content field appended when content is None
    assert b'name="content"' not in request.content


def test_channels_parses_page():
    payload = {
        "data": [
            {
                "id": "chan-1",
                "companyId": "company-1",
                "name": "General",
                "channelType": "public",
                "total": 10,
                "subscribed": True,
                "allCompany": True,
            }
        ],
        "meta": {"currentPage": 1, "lastPage": 1, "total": 1, "perPage": 20},
    }
    recorder = Recorder(payload)
    sdk = make_sdk(recorder)

    page = sdk.community.channels()

    assert recorder.last.url.path == "/private/community/v1/company/channels"
    assert page.data[0].name == "General"
    assert page.data[0].all_company is True
