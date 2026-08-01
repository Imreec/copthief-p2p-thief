"""Synthetic report-layer inputs (M6-2), imported by name to dodge conftest ambiguity.

Role-agnostic by construction (ops gotcha #9): neutral group ids, no per-repo config
values — the same fixtures must pass unchanged in the thief mirror.
"""

from __future__ import annotations

from typing import Any


def make_identity(gid: str, port: int) -> dict[str, Any]:
    """A seven-key handshake identity (F8b shape) with a full sysinfo-style spec."""
    return {
        "group_id": gid,
        "group_name": gid.title(),
        "members": ["m1", "m2"],
        "repos": {
            "cop": f"https://example.test/{gid}/cop",
            "thief": f"https://example.test/{gid}/thief",
        },
        "mcp_servers": {
            "cop": f"http://127.0.0.1:{port}/mcp",
            "thief": f"http://127.0.0.1:{port}/mcp",
        },
        "llm_model": "none",
        "spec": {
            "os": "TestOS 1.0",
            "cpu_type": "TestCPU",
            "cpu_cores": 4,
            "cpu_freq_mhz": 2000,
            "ram_gb": 16.0,
            "gpu_type": "TestGPU",
            "gpu_cores_or_cuda": "unknown",
            "vram_gb": 2.0,
        },
    }


def make_summary(
    *,
    sub_game_number: int = 1,
    role: str = "thief",
    result: str = "capture",
    winner: str = "police",
    steps: int = 2,
    tokens_total: int = 0,
    audit_passed: bool = True,
    github_commit: str | None = None,
) -> dict[str, Any]:
    """One reference-shaped per-sub-game summary (the M6-6 series runner's contract).

    `github_commit=None` mirrors the reference's own step-0 payload (which omits the
    key); a value mirrors OUR live seal (`live_spec_record` always includes it).
    """
    spec_payload: dict[str, Any] = {
        "step": 0,
        "type": "system_spec",
        "spec": {"os": "TestOS 1.0", "cpu_type": "TestCPU"},
        "model": "none",
        "code_version": "1.00",
        "group_name": role.title(),
        "sub_game_number": sub_game_number,
    }
    if github_commit is not None:
        spec_payload["github_commit"] = github_commit
    spec_record = {
        "payload": spec_payload,
        "nonce": "aa" * 16,
        "commit": "bb" * 32,
    }
    step_records = [
        {
            "payload": {
                "step": n,
                "state": f"grid=7x7;self=[{n}, 3];barriers=[]",
                "position": [n, 3],
                "move": "MOVE:S",
                "intent": "truth",
                "hint": f"hint {n}",
            },
            "nonce": f"{n:02d}" * 16,
            "commit": f"{n:02d}" * 32,
        }
        for n in range(1, steps + 1)
    ]
    history = [
        {
            "step": n,
            "timestamp": f"2026-07-19T10:00:0{n}+00:00",
            "sender": "police" if role == "thief" else "thief",
            "hint": f"their hint {n}",
            "smell_grid": {},
            "barrier_placed": None,
            "commit": f"{n:02d}" * 32,
        }
        for n in range(1, steps + 1)
    ]
    return {
        "sub_game_number": sub_game_number,
        "role": role,
        "result": result,
        "winner": winner,
        "steps": steps,
        "group_name": role.title(),
        "started_at": "2026-07-19T10:00:00+00:00",
        "duration_seconds": 30.0,
        "tokens_total": tokens_total,
        "audit": {"passed": audit_passed, "verified_steps": steps + 1, "failed_steps": []},
        "records": [spec_record, *step_records],
        "history": history,
    }
