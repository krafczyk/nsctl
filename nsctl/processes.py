import os, shlex, subprocess, shutil
import psutil
from collections.abc import Mapping
from typing import Literal

try:
    from typing import TypedDict, NotRequired
except ImportError:
    from typing_extensions import TypedDict, NotRequired

from nsctl.config import NSInfo
from nsctl.utils import get_uid, get_gid, check_ops


Escalate = Literal["sudo", "pkexec", None]


def _exec_cmd(cmd: list[str] | str,
              *,
              # orthogonal switches
              detach: bool = False,
              capture_output: bool = False,
              check: bool = False,
              dry_run: bool = False,
              verbose: bool = False,
              env: Mapping[str, str] | None = None,
              # namespace
              ns_pid: int | None = None,
              working_dir: str | None = None,
              # privilege
              escalate: Escalate = None,
              as_user: str | None = None,
              passthrough: bool = False,
              ) -> subprocess.CompletedProcess[str] | subprocess.Popen[str] | None:
    """
    Bottom level executor
    * `detach=True` -> returns immediately with `popen` handle; `capture_output`
                       must be false
    * `ns_pid`      -> if provided, prepends `nsenter -t <pid> --all --`.
    * `escalate`    -> prepend `sudo -n` or `pkexec` **once**, *before* nsenter.
    * `as_user`     -> translate to `--setuid/--setgid` when using nsenter.
    """
    # ----------------------- validate --------------------------
    if detach and capture_output:
        raise ValueError("Cannot use detach=True with capture_output=True.")
    if isinstance(cmd, str):
        cmd_args: list[str] = shlex.split(cmd)
    else:
        cmd_args = list(cmd)

    # ----------------------- nsenter --------------------------
    if ns_pid is not None:
        ns_cmd = ["nsenter", "-t", str(ns_pid), "--all"]
        if working_dir:
            ns_cmd.append(f"--wd={working_dir}")
        if as_user:
            uid = get_uid(as_user)
            gid = get_gid(as_user)
            ns_cmd += [f"--setuid={uid}", f"--setgid={gid}"]
        ns_cmd.append("--")
        cmd_args = ns_cmd + cmd_args

    # ----------------------- escalate --------------------------
    if escalate is not None:
        helper = shutil.which(escalate)
        if helper is None:
            raise RuntimeError(f"{escalate} not found in PATH; cannot escalate")
        cmd_args = [helper, "-n"] + cmd_args

    # ----------------------- dry-run --------------------------
    if dry_run:
        print("DRY-RUN:", " ".join(cmd_args))
        return None

    # ----------------------- execution path --------------------------
    if detach:
        stdin = subprocess.DEVNULL
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
        if passthrough:
            stdin = None
            stdout = None
            stderr = None
        if verbose:
            print(f"DETACH: {' '.join(cmd_args)}")
        return subprocess.Popen(
            cmd_args,
            stdout=stdout,
            stderr=stderr,
            stdin=stdin,
            env=env,
            start_new_session=True,
            text=True,
        )
    if verbose:
        print(f"RUN: {' '.join(cmd_args)}")
    stdin = None
    stdout = None
    stderr = None
    return subprocess.run(
        cmd_args,
        text=True,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        capture_output=capture_output,
        env=env,
        check=check
    )


def handle_ns(ns: NSInfo|None, escalate: Escalate = None) -> tuple[int|None,Escalate]:
    if ns is None:
        return (None, escalate)

    if escalate is None:
        if not check_ops(ns.namespaces):
            escalate = "sudo"
    return (ns.pid, escalate)


def run(cmd: list[str] | str,
        *,
        dry_run: bool = False,
        verbose: bool = False,
        env: Mapping[str, str] | None = None,
        escalate: Escalate = None,
        ns: NSInfo|None = None,
        as_user: str|None = None,) -> None:
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    _ = _exec_cmd(
        cmd,
        capture_output=False,
        check=False,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
    )

def run_check(cmd: list[str] | str,
              *,
              dry_run: bool = False,
              verbose: bool = False,
              env: Mapping[str, str] | None = None,
              escalate: Escalate = None,
              ns: NSInfo|None = None,
              as_user: str|None = None,) -> None:
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    _ = _exec_cmd(
        cmd,
        capture_output=False,
        check=True,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
    )


class RunCheckOutputArgs(TypedDict):
    dry_run: NotRequired[bool]
    verbose: NotRequired[bool]
    env: NotRequired[Mapping[str, str]]
    escalate: NotRequired[Escalate]
    ns: NotRequired[NSInfo]
    as_user: NotRequired[str]


def run_check_output(cmd: list[str] | str,
              *,
              dry_run: bool = False,
              verbose: bool = False,
              env: Mapping[str, str] | None = None,
              escalate: Escalate = None,
              ns: NSInfo|None = None,
              as_user: str|None = None,) -> str:
    """Runs a command, checks if the command failed, and returns the return code."""
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    result = _exec_cmd(
        cmd,
        capture_output=True,
        check=True,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
    )

    if type(result) is not subprocess.CompletedProcess:
        raise RuntimeError(f"Expected CompletedProcess, got {type(result)}")

    return result.stdout


def run_code_output(cmd: list[str] | str,
              *,
              dry_run: bool = False,
              verbose: bool = False,
              env: Mapping[str, str] | None = None,
              escalate: Escalate = None,
              ns: NSInfo|None = None,
              as_user: str|None = None,) -> tuple[int,str]:
    """Runs a command, checks if the command failed, and returns the return code."""
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    result = _exec_cmd(
        cmd,
        capture_output=True,
        check=True,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
    )

    if type(result) is not subprocess.CompletedProcess:
        raise RuntimeError(f"Expected CompletedProcess, got {type(result)}")

    return (result.returncode, result.stdout)


def run_check_code(cmd: list[str] | str,
                   *,
                   dry_run: bool = False,
                   verbose: bool = False,
                   env: Mapping[str, str] | None = None,
                   escalate: Escalate = None,
                   ns: NSInfo|None = None,
                   as_user: str|None = None,) -> int:
    """Runs a command, checks if the command failed, and returns the return code."""
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    result = _exec_cmd(
        cmd,
        capture_output=False,
        check=True,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
    )

    if type(result) is not subprocess.CompletedProcess:
        raise RuntimeError(f"Expected CompletedProcess, got {type(result)}")

    return result.returncode


def run_code_passthrough(cmd: list[str] | str,
                         *,
                         dry_run: bool = False,
                         verbose: bool = False,
                         env: Mapping[str, str] | None = None,
                         escalate: Escalate = None,
                         ns: NSInfo|None = None,
                         as_user: str|None = None,) -> int:
    """Runs a command, checks if the command failed, and returns the return code."""
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    # We don't throw an error if the command fails
    # We don't capture the output
    result = _exec_cmd(
        cmd,
        capture_output=False,
        check=False,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
        passthrough=True,
    )

    if type(result) is not subprocess.CompletedProcess:
        raise RuntimeError(f"Expected CompletedProcess, got {type(result)}")

    return result.returncode


def detach(
        cmd: list[str] | str,
        dry_run: bool = False,
        verbose: bool = False,
        env: Mapping[str, str] | None = None,
        escalate: Escalate = None,
        ns: NSInfo|None = None,
        as_user: str|None = None,) -> subprocess.Popen[str]:
    
    work_dir = os.getcwd()
    ns_pid, escalate = handle_ns(ns, escalate)

    result = _exec_cmd(
        cmd,
        detach=True,
        capture_output=False,
        check=False,
        env=env,
        escalate=escalate,
        dry_run=dry_run,
        verbose=verbose,
        ns_pid=ns_pid,
        as_user=as_user,
        working_dir=work_dir,
    )

    if not isinstance(result, subprocess.Popen):
        raise RuntimeError(f"Expected Popen, got {type(result)}")

    return result


def detach_and_check(
        cmd: list[str] | str,
        dry_run: bool = False,
        verbose: bool = False,
        env: Mapping[str, str] | None = None,
        escalate: Escalate = None,
        ns: NSInfo|None = None,
        as_user: str|None = None,
        wait_time: float = 1.) -> subprocess.Popen[str]:
    
    process = detach(
        cmd,
        dry_run=dry_run,
        verbose=verbose,
        env=env,
        escalate=escalate,
        ns=ns,
        as_user=as_user)

    # Wait for the process to start, and check that it didn't fail
    try:
        returncode = process.wait(timeout=wait_time)
        raise RuntimeError(
            f"Detached process exited immediately, indicating failure. returncode was: {returncode}")
    except subprocess.TimeoutExpired:
        pass

    return process


def find_bottom_children(pid: int) -> list[psutil.Process]:
    """
    Recursively returns a list of all leaf (bottom-most) processes
    in the process tree rooted at `pid`.
    """
    try:
        process = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []

    children = process.children()
    if not children:
        # This process has no children, so it's a bottom-most process
        return [process]

    # Otherwise, collect bottom-most children of each child
    bottom: list[psutil.Process] = []
    for child in children:
        bottom.extend(find_bottom_children(child.pid))
    return bottom


def process_exists(pid: int):
    if os.path.exists(f"/proc/{pid}"):
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
