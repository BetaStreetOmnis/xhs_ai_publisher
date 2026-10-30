"""Publication regression tests. Browser/account I/O is replaced; source is imported normally."""
import asyncio
import importlib
import json
import logging
import sys
from datetime import datetime, timedelta
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException

from src.core.services.publication_policy import PublicationNeedsReview


@pytest.fixture(scope="session")
def qt_application():
    from PyQt5.QtCore import QCoreApplication
    application = QCoreApplication.instance() or QCoreApplication([])
    yield application


@pytest.fixture
def runtime(monkeypatch, tmp_path, qt_application):
    monkeypatch.setenv("XHS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: None)
    # Keep legacy Desktop log destinations out of the real user's directories.
    for name in ("src.core.logger", "core.logger"):
        module = ModuleType(name)
        module.logger = logging.getLogger("publication-tests")
        monkeypatch.setitem(sys.modules, name, module)
    poster_module = importlib.import_module("src.core.write_xiaohongshu")
    web = importlib.import_module("src.web.app")
    scheduler = importlib.import_module("src.core.scheduler.schedule_manager")
    scheduler.schedule_manager.stop_scheduler()
    web.config.app.data_dir = str(tmp_path)
    manager = web.ContentManager()
    web.content_manager = manager
    web.publication_lock = asyncio.Lock()
    web.runtime_lock = asyncio.Lock()
    web.browser_generation = 0
    web.auth_manager = SimpleNamespace(is_logged_in=AsyncMock(return_value=True))
    monkeypatch.setattr(web, "ensure_basic_managers", lambda: None)
    monkeypatch.setattr(web, "ensure_browser_runtime", AsyncMock())
    poster = FakePublisher()
    web.publisher = poster
    result = SimpleNamespace(web=web, manager=manager, poster=poster,
                             poster_class=poster_module.XiaohongshuPoster,
                             scheduler=scheduler, directory=tmp_path, application=qt_application)
    yield result


class FakePublisher:
    def __init__(self):
        self.last_publish_status = "submitted"
        self._submission_attempted = False
        self.active = 0
        self.max_active = 0
        self.calls = []
        self.error = None
        self.false_result = False

    async def post_article(self, **payload):
        self.active += 1
        self.max_active = max(self.active, self.max_active)
        self.calls.append(payload)
        self._submission_attempted = payload["auto_publish"]
        try:
            await asyncio.sleep(0.01)
            if self.error:
                raise self.error
            return not self.false_result
        finally:
            self.active -= 1


def draft(runtime, title="真实项目记录", body="这是准备发布的真实项目记录"):
    return runtime.manager.create_content(title, body)


async def enqueue(runtime, content_id, automatic=False):
    tasks = BackgroundTasks()
    result = await runtime.web.publish_content(runtime.web.PublishRequest(content_id=content_id, auto_publish=automatic, review_confirmed=True, ai_usage="none"), tasks)
    return tasks, result


@pytest.mark.asyncio
async def test_http_manual_fill_stays_draft(runtime):
    content_id = draft(runtime)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=runtime.web.app), base_url="http://localhost") as client:
        response = await client.post("/api/publish", json={"content_id": content_id, "review_confirmed": True, "ai_usage": "none"})
        assert response.status_code == 200
        stored = (await client.get(f"/api/content/{content_id}")).json()["data"]
        assert stored["status"] == "draft"
        assert stored["published_at"] is None
    assert len(runtime.poster.calls) == 1
    assert runtime.poster.calls[0]["auto_publish"] is False


@pytest.mark.asyncio
async def test_http_requires_configured_token_before_publication(runtime, monkeypatch):
    monkeypatch.setenv("XHS_WEB_API_TOKEN", "test-access-token")
    content_id = draft(runtime)
    payload = {"content_id": content_id, "auto_publish": False, "review_confirmed": True, "ai_usage": "none"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=runtime.web.app), base_url="http://localhost") as client:
        rejected = await client.post("/api/publish", json=payload)
        assert rejected.status_code == 401
        assert not runtime.poster.calls
        accepted = await client.post("/api/publish", json=payload,
                                     headers={"Authorization": "Bearer test-access-token"})
        assert accepted.status_code == 200
    assert len(runtime.poster.calls) == 1


@pytest.mark.asyncio
async def test_two_distinct_http_requests_serialize_browser_calls(runtime):
    first, second = draft(runtime), draft(runtime, title="另一个项目记录")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=runtime.web.app), base_url="http://localhost") as client:
        responses = await asyncio.gather(*(client.post("/api/publish", json={"content_id": key, "auto_publish": False, "review_confirmed": True, "ai_usage": "none"})
                                           for key in (first, second)))
    assert all(response.status_code == 200 for response in responses)
    assert len(runtime.poster.calls) == 2
    assert runtime.poster.max_active == 1


@pytest.mark.asyncio
async def test_queued_request_already_blocks_duplicate(runtime):
    content_id = draft(runtime)
    tasks, _ = await enqueue(runtime, content_id)
    with pytest.raises(HTTPException) as error:
        await enqueue(runtime, content_id)
    assert error.value.status_code == 409
    await tasks()
    assert len(runtime.poster.calls) == 1


@pytest.mark.asyncio
async def test_raw_payload_duplicates_are_rejected(runtime):
    tasks = BackgroundTasks()
    request = runtime.web.PublishRequest(title="实际开发记录", content="项目的实际开发记录", auto_publish=False, review_confirmed=True, ai_usage="none")
    await runtime.web.publish_content(request, tasks)
    with pytest.raises(HTTPException) as error:
        await runtime.web.publish_content(request, BackgroundTasks())
    assert error.value.status_code == 409
    await tasks()
    assert len(runtime.poster.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["submitted", "under_review", "published", "unknown", "needs_review"])
async def test_unverified_or_accepted_posts_cannot_be_resubmitted(runtime, status):
    content_id = draft(runtime)
    runtime.manager.update_content_status(content_id, status)
    with pytest.raises(HTTPException) as error:
        await enqueue(runtime, content_id)
    assert error.value.status_code == 409
    assert not runtime.poster.calls


@pytest.mark.asyncio
async def test_content_modified_while_queued_is_not_sent(runtime):
    content_id = draft(runtime)
    tasks, _ = await enqueue(runtime, content_id)
    runtime.manager.update_content(content_id, content="排队后修改了正文")
    await tasks()
    assert runtime.manager.get_content(content_id).status == "needs_review"
    assert not runtime.poster.calls


@pytest.mark.asyncio
async def test_deleted_queued_content_is_not_sent(runtime):
    content_id = draft(runtime)
    tasks, _ = await enqueue(runtime, content_id)
    runtime.manager.delete_content(content_id)
    await tasks()
    assert not runtime.poster.calls


@pytest.mark.asyncio
async def test_login_change_while_queued_stops_publication(runtime):
    content_id = draft(runtime)
    tasks, _ = await enqueue(runtime, content_id)
    runtime.web.auth_manager.is_logged_in.return_value = False
    await tasks()
    assert runtime.manager.get_content(content_id).status == "needs_review"
    assert not runtime.poster.calls


@pytest.mark.asyncio
async def test_logout_then_relogin_cannot_redirect_queued_post_to_new_account(runtime):
    content_id = draft(runtime)
    tasks, _ = await enqueue(runtime, content_id)
    runtime.web.auth_manager.logout = AsyncMock(return_value=True)
    runtime.web.session_manager = SimpleNamespace(get_current_session=lambda: None)
    await runtime.web.logout()
    # Model a new signed-in account: a boolean login check would still pass.
    runtime.web.auth_manager.is_logged_in.return_value = True
    await tasks()
    assert runtime.manager.get_content(content_id).status == "needs_review"
    assert not runtime.poster.calls


@pytest.mark.asyncio
async def test_image_removed_while_queued_is_not_sent(runtime):
    content_id = draft(runtime)
    image = runtime.directory / "image.jpg"
    image.write_bytes(b"synthetic fixture")
    runtime.manager.add_image_to_content(content_id, str(image))
    tasks, _ = await enqueue(runtime, content_id)
    image.unlink()
    await tasks()
    assert runtime.manager.get_content(content_id).status == "needs_review"
    assert not runtime.poster.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [PublicationNeedsReview("人工核验"), RuntimeError("click timed out")])
async def test_post_submit_errors_stay_blocked(runtime, error):
    content_id = draft(runtime)
    runtime.poster.error = error
    tasks, _ = await enqueue(runtime, content_id)
    await tasks()
    assert runtime.manager.get_content(content_id).status == "needs_review"
    with pytest.raises(HTTPException):
        await enqueue(runtime, content_id)
    assert len(runtime.poster.calls) == 1


@pytest.mark.asyncio
async def test_false_result_is_not_a_retryable_failure(runtime):
    content_id = draft(runtime)
    runtime.poster.false_result = True
    tasks, _ = await enqueue(runtime, content_id)
    await tasks()
    assert runtime.manager.get_content(content_id).status == "needs_review"


@pytest.mark.asyncio
async def test_manual_preview_stays_draft(runtime):
    content_id = draft(runtime)
    tasks, _ = await enqueue(runtime, content_id, automatic=False)
    await tasks()
    assert runtime.manager.get_content(content_id).status == "draft"
    assert runtime.poster.calls[0]["auto_publish"] is False


@pytest.mark.asyncio
async def test_failed_reservation_write_never_starts_background_task(runtime, monkeypatch):
    content_id = draft(runtime)
    def fail():
        raise OSError("disk full")
    monkeypatch.setattr(runtime.manager, "_save_contents", fail)
    tasks = BackgroundTasks()
    with pytest.raises(HTTPException) as error:
        await runtime.web.publish_content(runtime.web.PublishRequest(content_id=content_id, auto_publish=False, review_confirmed=True, ai_usage="none"), tasks)
    assert error.value.status_code == 500
    assert not tasks.tasks
    assert not runtime.poster.calls


def test_web_restart_requires_verification_for_interrupted_tasks(runtime):
    content_id = draft(runtime)
    runtime.manager.update_content_status(content_id, "publishing")
    loaded = runtime.web.ContentManager()
    assert loaded.get_content(content_id).status == "needs_review"
    assert json.loads(loaded.content_file.read_text())[content_id]["status"] == "needs_review"


def test_scheduler_failure_stops_all_following_tasks(runtime):
    module = runtime.scheduler
    manager = module.ScheduleManager()
    manager.stop_scheduler()
    first = module.ScheduleTask("one", "first", datetime.now())
    second = module.ScheduleTask("two", "second", datetime.now())
    manager.tasks = [first, second]
    manager.handle_task_result("one", False, "未能确认结果，请人工核验")
    assert first.status == second.status == "needs_review"
    assert first.retry_count == 1
    assert not manager.get_pending_tasks()
    assert manager.running is False


def test_scheduler_restart_recovers_running_to_review(runtime):
    module = runtime.scheduler
    task = module.ScheduleTask("interrupted", "body", datetime.now() - timedelta(minutes=2))
    task.status = "running"
    path = runtime.directory / "schedule_tasks.json"
    path.write_text(json.dumps([task.to_dict()]))
    manager = module.ScheduleManager()
    manager.stop_scheduler()
    assert manager.tasks[0].status == "needs_review"
    assert not manager.get_pending_tasks()
    assert json.loads(path.read_text())[0]["status"] == "needs_review"


def test_scheduler_does_not_repeat_hotspots_after_submission(runtime):
    module = runtime.scheduler
    manager = module.ScheduleManager()
    manager.stop_scheduler()
    task = module.ScheduleTask("hot", "body", datetime.now(), task_type="hotspot", interval_hours=2)
    manager.tasks = [task]
    manager.handle_task_result("hot", True, "under_review")
    assert task.status == "needs_review"
    assert not manager.get_pending_tasks()


def test_scheduler_persistence_failure_prevents_dispatch(runtime, monkeypatch):
    module = runtime.scheduler
    manager = module.ScheduleManager()
    manager.stop_scheduler()
    task = module.ScheduleTask("disk", "body", datetime.now())
    emitted = []
    manager.task_execute_requested.connect(emitted.append)
    def fail():
        raise OSError("disk full")
    monkeypatch.setattr(manager, "save_tasks", fail)
    with pytest.raises(OSError):
        manager.execute_task(task)
    assert not emitted


def test_atomic_content_write_failure_preserves_previous_file(runtime, monkeypatch):
    content_id = draft(runtime)
    before = runtime.manager.content_file.read_bytes()
    module = importlib.import_module(runtime.manager.__class__.__module__)
    def fail(*args):
        raise OSError("replace failed")
    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(OSError):
        runtime.manager.update_content_status(content_id, "queued")
    assert runtime.manager.content_file.read_bytes() == before
    assert not list(runtime.manager.storage_dir.glob('.contents-*'))


def test_corrupt_history_does_not_silently_reset_duplicate_protection(runtime):
    runtime.manager.content_file.write_text("{bad json")
    with pytest.raises(json.JSONDecodeError):
        runtime.web.ContentManager()


def test_atomic_schedule_write_failure_preserves_previous_file(runtime, monkeypatch):
    module = runtime.scheduler
    manager = module.ScheduleManager()
    manager.stop_scheduler()
    manager.tasks = [module.ScheduleTask("saved", "body", datetime.now())]
    manager.save_tasks()
    before = (runtime.directory / "schedule_tasks.json").read_bytes()
    def fail(*args):
        raise OSError("replace failed")
    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(OSError):
        manager.save_tasks()
    assert (runtime.directory / "schedule_tasks.json").read_bytes() == before
    assert not list(runtime.directory.glob('.schedule-*'))


class Page:
    def __init__(self, text="", dialog=False, url="https://creator.xiaohongshu.com/error"):
        self.text = text
        self.dialog = dialog
        self.url = url

    def locator(self, selector):
        return SimpleNamespace(count=AsyncMock(return_value=int(self.dialog)),
                               nth=lambda index: SimpleNamespace(is_visible=AsyncMock(return_value=True)))

    def get_by_text(self, text, exact=False):
        return SimpleNamespace(first=SimpleNamespace(is_visible=AsyncMock(return_value=text == self.text)))


def confirmation_poster(runtime, text="", dialog=False):
    poster = runtime.poster_class.__new__(runtime.poster_class)
    poster.page = Page(text, dialog)
    poster.last_publish_status = "unknown"
    poster._has_blocking_auth_issue = AsyncMock(return_value=False)
    poster._dump_page_debug = AsyncMock()
    return poster


@pytest.mark.asyncio
async def test_final_publish_button_cannot_be_called_directly(runtime):
    poster = confirmation_poster(runtime)
    button = SimpleNamespace(click=AsyncMock())
    with pytest.raises(PublicationNeedsReview, match="自动提交已停用"):
        await poster._click_final_publish_button(button)
    button.click.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("text, status", [("审核中", "under_review"), ("发布成功", "submitted"), ("发布完成", "submitted")])
async def test_browser_confirmation_keeps_submission_distinct_from_publication(runtime, text, status):
    poster = confirmation_poster(runtime, text)
    assert await poster._wait_for_publication_result(timeout_seconds=1)
    assert poster.last_publish_status == status
    assert status != "published"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "发布中", "已发布"])
async def test_url_change_and_nonterminal_labels_do_not_mean_success(runtime, text):
    poster = confirmation_poster(runtime, text)
    with pytest.raises(PublicationNeedsReview):
        await poster._wait_for_publication_result(timeout_seconds=0.01)
    assert poster.last_publish_status == "unknown"


@pytest.mark.asyncio
async def test_unknown_dialog_stops_even_when_success_text_exists(runtime):
    poster = confirmation_poster(runtime, "发布成功", dialog=True)
    with pytest.raises(PublicationNeedsReview):
        await poster._wait_for_publication_result(timeout_seconds=1)
    assert poster.last_publish_status == "unknown"


@pytest.mark.asyncio
async def test_blocking_auth_issue_stops_confirmation(runtime):
    poster = confirmation_poster(runtime, "发布成功")
    poster._has_blocking_auth_issue.return_value = True
    with pytest.raises(PublicationNeedsReview):
        await poster._wait_for_publication_result(timeout_seconds=1)


def test_hotspot_model_failure_cannot_return_fallback_payload(runtime, monkeypatch):
    browser = importlib.import_module("src.core.browser")
    config = ModuleType("src.config.config")
    config.Config = lambda: SimpleNamespace(get_title_config=lambda: {})
    hotspot = ModuleType("src.core.services.hotspot_service")
    hotspot.hotspot_service = SimpleNamespace(fetch=lambda *args, **kwargs: [SimpleNamespace(title="实际新闻事件")])
    llm = ModuleType("src.core.services.llm_service")
    def fail(**kwargs):
        raise RuntimeError("provider unavailable")
    llm.llm_service = SimpleNamespace(generate_xiaohongshu_content=fail)
    for module in (config, hotspot, llm):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    with pytest.raises(PublicationNeedsReview):
        browser.BrowserThread._build_hotspot_payload_sync({"hotspot_source": "baidu", "use_hotspot_context": False})


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"auto_publish": True, "review_confirmed": True, "ai_usage": "none"},
    {},
    {"review_confirmed": True},
    {"review_confirmed": True, "ai_usage": "unknown"},
    {"review_confirmed": True, "ai_usage": "assisted"},
])
async def test_http_rejects_unattended_or_unreviewed_calls_before_io(runtime, payload):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=runtime.web.app), base_url="http://localhost") as client:
        response = await client.post("/api/publish", json={"title": "标题", "content": "正文", **payload})
        assert response.status_code == 400
    runtime.web.ensure_browser_runtime.assert_not_awaited()
    assert not runtime.manager.list_contents()
    assert not runtime.poster.calls


@pytest.mark.asyncio
async def test_api_allows_reviewed_ai_draft_for_manual_fill(runtime):
    tasks = BackgroundTasks()
    request = runtime.web.PublishRequest(content_id=draft(runtime), review_confirmed=True,
                                         ai_usage="assisted", ai_disclosure_confirmed=True)
    result = await runtime.web.publish_content(request, tasks)
    await tasks()
    assert result["auto_publish"] is False
    assert runtime.poster.calls[0]["auto_publish"] is False


@pytest.mark.asyncio
async def test_core_blocks_legacy_autopublish_before_browser_io(runtime, monkeypatch):
    monkeypatch.setenv("XHS_ENABLE_STEALTH_SCRIPT", "true")
    monkeypatch.setenv("XHS_ENABLE_FORCE_DOM_ACTIONS", "true")
    poster = runtime.poster_class.__new__(runtime.poster_class)
    poster.ensure_browser = AsyncMock()
    with pytest.raises(PublicationNeedsReview, match="自动提交已停用"):
        await poster.post_article("标题", "正文", [], auto_publish=True)
    poster.ensure_browser.assert_not_awaited()
    assert not poster._allow_force_dom_actions(manual_mode=True)


def schedule_manager(runtime):
    manager = runtime.scheduler.ScheduleManager()
    manager.stop_scheduler()
    manager.tasks = []
    return manager


def test_fixed_due_task_reminds_once_and_survives_restart(runtime):
    manager = schedule_manager(runtime)
    key = manager.add_task("待核实内容", datetime.now() - timedelta(seconds=1), title="标题")
    reminded, dispatched = [], []
    manager.task_reminded.connect(reminded.append)
    manager.task_execute_requested.connect(dispatched.append)
    manager.running = True
    manager.check_tasks()
    manager.check_tasks()
    assert reminded == [key]
    assert not dispatched
    assert manager.tasks[0].status == "reminded"
    loaded = runtime.scheduler.ScheduleManager()
    loaded.stop_scheduler()
    assert loaded.tasks[0].content == "待核实内容"
    assert loaded.tasks[0].status == "reminded"
    assert not loaded.get_pending_tasks()


def test_legacy_tasks_migrate_to_single_run_without_account_login(runtime):
    task = runtime.scheduler.ScheduleTask("legacy", "body", datetime.now(), task_type="hotspot")
    record = task.to_dict()
    record.pop("execution_policy")
    record["interval_hours"] = 2
    path = runtime.directory / "schedule_tasks.json"
    path.write_text(json.dumps([record]))
    manager = runtime.scheduler.ScheduleManager()
    manager.stop_scheduler()
    assert manager.tasks[0].interval_hours == 0
    assert "不会自动发布" in manager.tasks[0].error_message
    assert json.loads(path.read_text())[0]["execution_policy"] == "reminder_or_draft_v1"


def test_hotspot_draft_persists_owned_images_and_sources(runtime):
    manager = schedule_manager(runtime)
    key = manager.add_task("", datetime.now(), task_type="hotspot", interval_hours=2)
    dispatched = []
    manager.task_execute_requested.connect(dispatched.append)
    task = manager.tasks[0]
    manager.execute_task(task)
    source = runtime.directory / "temporary.png"
    source.write_bytes(b"image fixture")
    payload = {"title": "核实前草稿", "content": "数据待核实", "images": [str(source)],
               "source_url": "https://example.com/source", "hotspot_title": "原始标题",
               "reference_snippets": [{"url": "https://example.com/story", "snippet": "摘要"}]}
    manager.handle_draft_result(key, payload)
    source.unlink()
    loaded = runtime.scheduler.ScheduleManager()
    loaded.stop_scheduler()
    stored = loaded.tasks[0]
    assert len(dispatched) == 1
    assert stored.status == "draft_ready"
    assert stored.interval_hours == 0
    assert stored.content == "数据待核实"
    assert stored.source_metadata["review_required"] is True
    assert stored.source_metadata["source_url"] == payload["source_url"]
    assert stored.source_metadata["reference_snippets"] == payload["reference_snippets"]
    from pathlib import Path
    assert Path(stored.images[0]).read_bytes() == b"image fixture"
    loaded.clear_completed_tasks()
    assert loaded.tasks[0].task_id == key
    assert Path(stored.images[0]).exists()
    assert not loaded.get_pending_tasks()


@pytest.mark.parametrize("payload", [{}, {"content": "草稿", "images": ["/missing.png"]}])
def test_invalid_hotspot_result_never_signals_saved(runtime, payload):
    manager = schedule_manager(runtime)
    key = manager.add_task("", datetime.now(), task_type="hotspot")
    manager.execute_task(manager.tasks[0])
    completed = []
    manager.task_completed.connect(completed.append)
    manager.handle_draft_result(key, payload)
    assert not completed
    assert manager.tasks[0].status == "needs_review"


def test_image_copy_failure_does_not_keep_temporary_paths(runtime, monkeypatch):
    manager = schedule_manager(runtime)
    source = runtime.directory / "temporary.png"
    source.write_bytes(b"fixture")
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(runtime.scheduler.shutil, "copy2", fail)
    with pytest.raises(OSError):
        manager.add_task("body", datetime.now(), images=[str(source)])
    assert not manager.tasks


def test_deleted_hotspot_task_cannot_be_resurrected(runtime):
    manager = schedule_manager(runtime)
    key = manager.add_task("", datetime.now(), task_type="hotspot")
    manager.execute_task(manager.tasks[0])
    manager.remove_task(key)
    manager.handle_draft_result(key, {"content": "late callback"})
    assert not manager.tasks


def test_saved_signal_is_not_emitted_on_storage_failure(runtime, monkeypatch):
    manager = schedule_manager(runtime)
    key = manager.add_task("", datetime.now(), task_type="hotspot")
    manager.execute_task(manager.tasks[0])
    completed = []
    manager.task_completed.connect(completed.append)
    def fail():
        raise OSError("disk full")
    monkeypatch.setattr(manager, "save_tasks", fail)
    manager.handle_draft_result(key, {"content": "draft"})
    assert not completed
    assert manager.tasks[0].status == "needs_review"


@pytest.mark.asyncio
async def test_scheduled_worker_only_builds_draft_and_never_creates_poster(runtime, monkeypatch):
    from src.core.browser import BrowserThread
    worker = BrowserThread()
    generated = []
    worker.scheduled_task_draft_ready.connect(lambda key, payload: generated.append((key, payload)))
    payload = {"title": "标题", "content": "待核实草稿", "images": []}
    monkeypatch.setattr(worker, "_build_hotspot_payload_sync", lambda action: payload)
    await worker._run_scheduled_publish({"task_id": "hot", "task_type": "hotspot"})
    runtime.application.processEvents()
    assert generated == [("hot", payload)]
    assert worker.poster is None
    generated.clear()
    await worker._run_scheduled_publish({"task_id": "fixed", "task_type": "fixed"})
    assert not generated
    assert worker.poster is None



def test_late_legacy_acknowledgement_cannot_overwrite_saved_draft(runtime):
    manager = schedule_manager(runtime)
    key = manager.add_task("", datetime.now(), task_type="hotspot")
    manager.execute_task(manager.tasks[0])
    manager.handle_draft_result(key, {"content": "已保存草稿"})
    manager.handle_task_result(key, True, "under_review")
    manager.handle_task_result(key, False, "迟到的错误")
    assert manager.tasks[0].status == "draft_ready"
    assert manager.tasks[0].content == "已保存草稿"


def test_hotspot_builder_keeps_sources_and_avoids_second_marketing_generation(runtime, monkeypatch):
    browser = importlib.import_module("src.core.browser")
    captured = []
    config = ModuleType("src.config.config")
    config.Config = lambda: SimpleNamespace(get_title_config=lambda: {})
    hotspot = ModuleType("src.core.services.hotspot_service")
    snippets = [{"url": "https://example.com/report", "snippet": "未经核实的摘要"}]
    hotspot.hotspot_service = SimpleNamespace(
        fetch=lambda *args, **kwargs: [SimpleNamespace(title="热榜标题", url="https://example.com/list")],
        fetch_baidu_search_snippets=lambda *args, **kwargs: snippets,
    )
    llm = ModuleType("src.core.services.llm_service")
    def generate(**kwargs):
        captured.append(kwargs["topic"])
        return SimpleNamespace(title="待核实标题", content="待核实正文")
    llm.llm_service = SimpleNamespace(generate_xiaohongshu_content=generate)
    renderer = ModuleType("src.core.services.system_image_template_service")
    renderer.system_image_template_service = SimpleNamespace(
        resolve_showcase_dir=lambda: None, generate_post_images=lambda **kwargs: ("cover.png", []),
    )
    for module in (config, hotspot, llm, renderer):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    payload = browser.BrowserThread._build_hotspot_payload_sync({"cover_template_id": "showcase_marketing_poster"})
    assert len(captured) == 1
    assert "不要编造亲身体验" in captured[0]
    assert "不确定的信息明确写为待核实" in captured[0]
    assert payload["content"] == "待核实正文"
    assert payload["source_url"] == "https://example.com/list"
    assert payload["reference_snippets"] == snippets
