"""Dependency container: settings, repositories, providers, engines and the job executor."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.analytics.resilience import CalibratedResilienceEngine, ResilienceEngine
from app.config import Settings
from app.providers.cdl import CdlClient
from app.providers.hls import HlsClient
from app.providers.http import EarthdataAuth, HttpAcquirer
from app.providers.power import PowerClient
from app.providers.smap import SmapClient
from app.providers.srtm import SrtmClient
from app.providers.ssurgo import SsurgoClient
from app.repositories import Repositories, SqliteDocumentStore
from app.rotation.engine import MultiYearRotationEngine, PendingRotationEngine, RotationEngine
from app.rotation.kb import CropKnowledgeBase, load_kb
from app.suitability.engine import CropSuitabilityEngine


@dataclass
class Providers:
    power: PowerClient
    ssurgo: SsurgoClient
    cdl: CdlClient
    srtm: SrtmClient
    hls: HlsClient | None = None
    smap: SmapClient | None = None


@dataclass
class Container:
    settings: Settings
    repos: Repositories
    providers: Providers
    kb: CropKnowledgeBase
    resilience: ResilienceEngine
    rotation: RotationEngine
    executor: ThreadPoolExecutor | None = field(default=None)
    suitability: CropSuitabilityEngine | None = field(default=None)

    def __post_init__(self) -> None:
        if self.suitability is None:
            self.suitability = CropSuitabilityEngine(self.kb)

    def shutdown(self) -> None:
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)


def build_providers(settings: Settings, repos: Repositories, transport=None) -> Providers:
    http = HttpAcquirer(
        settings.cache_dir, retries=settings.http_retries, backoff_base_s=settings.http_backoff_base_s,
        timeout_s=settings.http_timeout_s, record_sink=lambda r: repos.acquisitions.put(str(r.acquisition_id), r),
        transport=transport,
    )

    def auth_factory() -> EarthdataAuth:
        return EarthdataAuth(
            token=settings.earthdata_token.get_secret_value() if settings.earthdata_token else None,
            username=settings.earthdata_username,
            password=settings.earthdata_password.get_secret_value() if settings.earthdata_password else None,
        )

    return Providers(
        power=PowerClient(http),
        ssurgo=SsurgoClient(http),
        cdl=CdlClient(http, download_timeout_s=settings.http_download_timeout_s),
        srtm=SrtmClient(http, settings.cache_dir / "derived", auth_factory,
                        download_timeout_s=settings.http_download_timeout_s),
        hls=HlsClient(http, settings.cache_dir / "derived", auth_factory, timeout_s=settings.http_timeout_s),
        smap=SmapClient(http, auth_factory, timeout_s=settings.http_timeout_s),
    )


def build_container(settings: Settings, *, providers: Providers | None = None, transport=None) -> Container:
    repos = Repositories.create(SqliteDocumentStore(settings.db_path))
    return Container(
        settings=settings,
        repos=repos,
        providers=providers or build_providers(settings, repos, transport),
        kb=load_kb(settings.crop_kb_dir),
        resilience=CalibratedResilienceEngine(),
        rotation=MultiYearRotationEngine(),
        executor=ThreadPoolExecutor(max_workers=settings.job_workers, thread_name_prefix="soilstice-job")
        if settings.job_execution == "thread" else None,
    )
