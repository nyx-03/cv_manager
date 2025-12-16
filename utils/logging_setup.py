import atexit
import logging
import logging.handlers
import os
import queue
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "CV Manager"
DEFAULT_LOGGER_NAME = "cv_manager"


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """
    Configuration simple et stable.

    Note: `slots=True` (dataclasses) aide à réduire l'empreinte mémoire
    et sécurise l'objet config (frozen).
    """
    level: str = "INFO"
    to_console: bool = True
    to_file: bool = True
    max_bytes: int = 2_000_000
    backup_count: int = 5
    queue_maxsize: int = 10_000


class LoggingManager:
    """
    Gestionnaire de logging asynchrone.
    - Ajoute un QueueHandler sur le logger applicatif.
    - Draine vers console + fichier via QueueListener.

    Python 3.14: `QueueListener` implémente le protocole context manager.
    On l'utilise ici pour garantir un start/stop propre même en cas d'exception.
    """

    def __init__(
        self,
        logger: logging.Logger,
        listener: logging.handlers.QueueListener,
    ) -> None:
        self.logger = logger
        self._listener = listener
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        # Python 3.14: QueueListener est un context manager, donc __enter__ démarre proprement.
        # (Equivalent à listener.start(), mais permet aussi un __exit__ standard.)
        self._listener.__enter__()  # type: ignore[call-arg]
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self._listener.__exit__(None, None, None)  # type: ignore[call-arg]
        finally:
            self._started = False

    def __enter__(self) -> "LoggingManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


def _level(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return getattr(logging, str(value).upper(), logging.INFO)


def _default_log_dir() -> Path:
    """
    Choisit un dossier de logs "standard" selon l'OS.
    - macOS: ~/Library/Application Support/CV Manager/logs
    - Windows: %APPDATA%\\CV Manager\\logs
    - Linux: ~/.local/state/cv_manager/logs
    """
    home = Path.home()

    if sys.platform == "darwin":
        base = home / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))) / APP_NAME
    else:
        base = home / ".local" / "state" / "cv_manager"

    return base / "logs"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _make_formatter() -> logging.Formatter:
    # Format simple, lisible et stable (important pour le support).
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    return logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")


def _install_excepthooks(logger: logging.Logger) -> None:
    """
    Capture les exceptions non gérées.
    Très utile lorsque l'app est lancée depuis Finder (PyInstaller),
    où la console n'est pas visible.
    """

    def excepthook(exc_type, exc, tb):
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = excepthook

    # Exceptions non catchées dans les threads Python.
    if hasattr(sys, "threading_excepthook"):
        def threading_excepthook(args):
            logger.critical(
                "Unhandled thread exception",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        sys.threading_excepthook = threading_excepthook  # type: ignore[attr-defined]


def setup_logging(
    *,
    config: LoggingConfig | None = None,
    log_dir: Path | None = None,
    logger_name: str = DEFAULT_LOGGER_NAME,
) -> LoggingManager:
    """
    Point d'entrée unique: configure le logger applicatif et renvoie un LoggingManager.

    Usage recommandé dans main.py (tout début du programme):
        mgr = setup_logging()
        mgr.start()
        ...
        # stop automatique via atexit, ou mgr.stop()
    """
    cfg = config or LoggingConfig()
    lvl = _level(cfg.level)

    logger = logging.getLogger(logger_name)
    logger.setLevel(lvl)
    logger.propagate = False

    # Évite les doubles configurations (relance / hot-reload / tests).
    if getattr(logger, "_cvmanager_logging_configured", False):
        # On renvoie un manager "no-op" mais cohérent.
        dummy_listener = logging.handlers.QueueListener(queue.Queue())
        mgr = LoggingManager(logger=logger, listener=dummy_listener)
        mgr._started = True
        return mgr

    formatter = _make_formatter()

    # Les handlers "réels" (console/fichier) seront portés par le QueueListener
    sinks: list[logging.Handler] = []

    if cfg.to_console:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(lvl)
        ch.setFormatter(formatter)
        sinks.append(ch)

    if cfg.to_file:
        env_path = os.environ.get("CV_MANAGER_LOG_FILE", "").strip()
        if env_path:
            logfile = Path(env_path).expanduser()
            logs = logfile.parent
        else:
            logs = log_dir or _default_log_dir()
            logfile = logs / "cv_manager.log"

        _ensure_dir(logs)

        fh = logging.handlers.RotatingFileHandler(
            logfile,
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        )
        fh.setLevel(lvl)
        fh.setFormatter(formatter)
        sinks.append(fh)

    # Queue: évite de bloquer le thread UI (Qt) lors d'écritures disque/console.
    q: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=cfg.queue_maxsize)

    qh = logging.handlers.QueueHandler(q)
    qh.setLevel(lvl)

    logger.addHandler(qh)

    listener = logging.handlers.QueueListener(
        q,
        *sinks,
        respect_handler_level=True,
    )

    mgr = LoggingManager(logger=logger, listener=listener)

    # Stop propre à la sortie (même si l'app est fermée brutalement).
    atexit.register(mgr.stop)

    _install_excepthooks(logger)

    logger._cvmanager_logging_configured = True  # type: ignore[attr-defined]
    logger.info("Logging configured")
    return mgr
