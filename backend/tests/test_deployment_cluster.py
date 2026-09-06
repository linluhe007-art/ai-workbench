"""
Phase 4.25 tests - ClusterManager, LeaderElection, GracefulShutdown, ReadinessProbe
"""
import pytest
from app.deployment.cluster import ClusterManager, ClusterInstance
from app.deployment.leader import LeaderElection, LeaderInfo
from app.deployment.readiness import GracefulShutdown, ReadinessProbe, ShutdownPhase, ShutdownReport


class TestClusterInstance:
    def test_create_instance(self):
        inst = ClusterInstance(instance_id="i1")
        assert inst.instance_id == "i1"
        assert inst.status == "starting"
        assert inst.role == "worker"

    def test_to_dict(self):
        inst = ClusterInstance(instance_id="i1", host="h1", port=9000, status="healthy", role="leader")
        d = inst.to_dict()
        assert d["instance_id"] == "i1"
        assert d["host"] == "h1"
        assert d["port"] == 9000
        assert d["role"] == "leader"

    def test_default_metadata(self):
        inst = ClusterInstance(instance_id="x")
        assert inst.metadata == {}


class TestClusterManagerInMemory:
    @pytest.mark.asyncio
    async def test_register(self):
        cm = ClusterManager(instance_id="inst-1")
        inst = await cm.register()
        assert inst.instance_id == "inst-1"
        assert inst.status == "healthy"

    @pytest.mark.asyncio
    async def test_discover_self(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        instances = await cm.discover()
        assert len(instances) == 1
        assert instances[0].instance_id == "inst-1"

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        await cm.heartbeat()
        instances = await cm.discover()
        assert instances[0].last_heartbeat is not None

    @pytest.mark.asyncio
    async def test_deregister(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        await cm.deregister()
        instances = await cm.discover()
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_cluster_health(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        health = await cm.cluster_health()
        assert health["total_instances"] == 1
        assert health["healthy_instances"] == 1
        assert health["self"] == "inst-1"

    @pytest.mark.asyncio
    async def test_no_leader_without_election(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        leader = await cm.get_leader()
        assert leader is None


class TestLeaderElection:
    def test_no_redis_self_leader(self):
        le = LeaderElection(instance_id="inst-1")
        assert le.is_leader is False

    @pytest.mark.asyncio
    async def test_campaign_no_redis(self):
        le = LeaderElection(instance_id="inst-1")
        result = await le.campaign()
        assert result is True
        assert le.is_leader is True

    @pytest.mark.asyncio
    async def test_step_down_no_redis(self):
        le = LeaderElection(instance_id="inst-1")
        await le.campaign()
        await le.step_down()
        assert le.is_leader is False

    @pytest.mark.asyncio
    async def test_get_current_leader_no_redis(self):
        le = LeaderElection(instance_id="inst-1")
        leader = await le.get_current_leader()
        assert leader == "inst-1"

    def test_get_info(self):
        le = LeaderElection(instance_id="inst-1")
        info = le.get_info()
        assert isinstance(info, LeaderInfo)
        assert info.instance_id == ""

    @pytest.mark.asyncio
    async def test_get_info_after_campaign(self):
        le = LeaderElection(instance_id="inst-1")
        await le.campaign()
        info = le.get_info()
        assert info.instance_id == "inst-1"
        assert info.term == 1

    def test_leader_info_to_dict(self):
        info = LeaderInfo(instance_id="i1", elected_at="2026-01-01T00:00:00", term=1)
        d = info.to_dict()
        assert d["instance_id"] == "i1"
        assert d["term"] == 1


class TestReadinessProbe:
    def test_default_ready(self):
        probe = ReadinessProbe()
        assert probe.is_ready is True

    def test_mark_not_ready(self):
        probe = ReadinessProbe()
        probe.mark_not_ready()
        assert probe.is_ready is False

    def test_mark_ready(self):
        probe = ReadinessProbe()
        probe.mark_not_ready()
        probe.mark_ready()
        assert probe.is_ready is True


class TestGracefulShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_succeeds(self):
        gs = GracefulShutdown()
        report = await gs.shutdown()
        assert report.phase == ShutdownPhase.STOPPED
        assert report.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_shutdown_report_to_dict(self):
        gs = GracefulShutdown()
        report = await gs.shutdown()
        d = report.to_dict()
        assert "phase" in d
        assert d["phase"] == "stopped"

    @pytest.mark.asyncio
    async def test_shutdown_phases_progress(self):
        gs = GracefulShutdown()
        report = await gs.shutdown()
        assert report.state_saved is False  # No runtime attached
        assert report.connections_closed is True

    def test_shutdown_phase_enum(self):
        assert ShutdownPhase.RUNNING.value == "running"
        assert ShutdownPhase.STOPPED.value == "stopped"

    def test_shutdown_report_defaults(self):
        report = ShutdownReport()
        assert report.phase == ShutdownPhase.RUNNING
        assert report.tasks_drained == 0
        assert report.errors == []

class TestClusterManagerEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_heartbeats(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        for _ in range(3):
            await cm.heartbeat()
        instances = await cm.discover()
        assert len(instances) == 1

    @pytest.mark.asyncio
    async def test_discover_before_register(self):
        cm = ClusterManager(instance_id="inst-1")
        instances = await cm.discover()
        assert instances == []

    @pytest.mark.asyncio
    async def test_deregister_twice(self):
        cm = ClusterManager(instance_id="inst-1")
        await cm.register()
        await cm.deregister()
        await cm.deregister()
        instances = await cm.discover()
        assert len(instances) == 0


class TestGracefulShutdownExtended:
    @pytest.mark.asyncio
    async def test_shutdown_with_probe(self):
        probe = ReadinessProbe()
        gs = GracefulShutdown(readiness_probe=probe)
        await gs.shutdown()
        assert probe.is_ready is False

    @pytest.mark.asyncio
    async def test_shutdown_phases_all_visited(self):
        gs = GracefulShutdown()
        await gs.shutdown()
        assert gs.phase == ShutdownPhase.STOPPED

    def test_shutdown_report_errors_initial(self):
        report = ShutdownReport()
        assert report.errors == []
        assert report.state_saved is False


class TestClusterInstanceExtended:
    def test_instance_unique_ids(self):
        i1 = ClusterInstance(instance_id="a")
        i2 = ClusterInstance(instance_id="b")
        assert i1.instance_id != i2.instance_id

class TestClusterManagerMultipleInstances:
    @pytest.mark.asyncio
    async def test_two_managers_independent(self):
        cm1 = ClusterManager(instance_id="inst-a")
        cm2 = ClusterManager(instance_id="inst-b")
        await cm1.register()
        await cm2.register()
        a_instances = await cm1.discover()
        b_instances = await cm2.discover()
        assert len(a_instances) == 1 or len(b_instances) == 1


class TestGracefulShutdownPhases:
    def test_all_phases_exist(self):
        phases = list(ShutdownPhase)
        assert ShutdownPhase.RUNNING in phases
        assert ShutdownPhase.DRAINING in phases
        assert ShutdownPhase.WAITING in phases
        assert ShutdownPhase.SAVING in phases
        assert ShutdownPhase.RELEASING in phases
        assert ShutdownPhase.CLOSING in phases
        assert ShutdownPhase.STOPPED in phases

    def test_phase_count(self):
        assert len(ShutdownPhase) == 7


class TestClusterInstanceEdge:
    def test_instance_different_roles(self):
        leader = ClusterInstance(instance_id="l", role="leader")
        worker = ClusterInstance(instance_id="w", role="worker")
        assert leader.role == "leader"
        assert worker.role == "worker"

    def test_instance_to_dict_all_fields(self):
        inst = ClusterInstance(
            instance_id="i1", host="h", port=8001, status="healthy",
            role="leader", started_at="t0", last_heartbeat="t1",
            metadata={"v": "1.0"}
        )
        d = inst.to_dict()
        for k in ["instance_id", "host", "port", "status", "role", "started_at", "last_heartbeat", "metadata"]:
            assert k in d


class TestLeaderElectionExtended:
    @pytest.mark.asyncio
    async def test_campaign_twice(self):
        le = LeaderElection(instance_id="inst-1")
        await le.campaign()
        info1 = le.get_info()
        await le.step_down()
        await le.campaign()
        info2 = le.get_info()
        assert info2.term > info1.term

    @pytest.mark.asyncio
    async def test_refresh_when_not_leader(self):
        le = LeaderElection(instance_id="inst-1")
        ok = await le.refresh()
        assert ok is False


class TestShutdownReportExtended:
    def test_report_all_fields(self):
        report = ShutdownReport(
            phase=ShutdownPhase.STOPPED,
            tasks_drained=5,
            tasks_remaining=0,
            state_saved=True,
            locks_released=True,
            connections_closed=True,
            duration_ms=250.0,
            errors=["e1"],
        )
        d = report.to_dict()
        assert d["tasks_drained"] == 5
        assert d["state_saved"] is True
        assert d["errors"] == ["e1"]

    def test_report_default_errors_empty(self):
        report = ShutdownReport()
        assert report.errors == []


class TestReadinessProbeExtended:
    def test_toggle_multiple(self):
        probe = ReadinessProbe()
        for _ in range(3):
            probe.mark_not_ready()
            assert probe.is_ready is False
            probe.mark_ready()
            assert probe.is_ready is True

class TestClusterManagerInstanceFields:
    def test_instance_default_port(self):
        inst = ClusterInstance(instance_id="i")
        assert inst.port == 8000

    def test_instance_default_host(self):
        inst = ClusterInstance(instance_id="i")
        assert inst.host == "localhost"

    def test_instance_custom_port(self):
        inst = ClusterInstance(instance_id="i", port=9000)
        assert inst.port == 9000


class TestLeaderElectionNoRedis:
    @pytest.mark.asyncio
    async def test_leader_info_default(self):
        le = LeaderElection(instance_id="i")
        info = le.get_info()
        assert info.term == 0
        assert info.elected_at == ""

    @pytest.mark.asyncio
    async def test_refresh_no_redis_still_leader(self):
        le = LeaderElection(instance_id="i")
        await le.campaign()
        ok = await le.refresh()
        assert ok is True


class TestGracefulShutdownAllPhases:
    @pytest.mark.asyncio
    async def test_shutdown_no_runtime(self):
        gs = GracefulShutdown()
        report = await gs.shutdown()
        assert report.locks_released is True
        assert report.state_saved is False

    def test_probe_default_ready(self):
        probe = ReadinessProbe()
        assert probe.is_ready

    def test_shutdown_phase_string_values(self):
        assert str(ShutdownPhase.DRAINING.value) == "draining"
        assert str(ShutdownPhase.STOPPED.value) == "stopped"


class TestClusterManagerNoRedis:
    @pytest.mark.asyncio
    async def test_leader_none_without_election(self):
        cm = ClusterManager(instance_id="i")
        await cm.register()
        leader = await cm.get_leader()
        assert leader is None

    @pytest.mark.asyncio
    async def test_set_leader_none(self):
        cm = ClusterManager(instance_id="i")
        await cm.set_leader(None)
        leader = await cm.get_leader()
        assert leader is None


class TestShutdownReportValues:
    def test_zero_values(self):
        r = ShutdownReport()
        d = r.to_dict()
        assert d["tasks_drained"] == 0
        assert d["tasks_remaining"] == 0
        assert d["duration_ms"] == 0.0