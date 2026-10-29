"""Local educational web app for password hashing demonstrations."""

from __future__ import annotations

import hashlib
import itertools
import json
import time
from typing import Any, Iterable

import bcrypt
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

DICT_EN = [
    "123456", "password", "dragon", "qwerty", "letmein", "monkey",
    "football", "iloveyou", "admin", "welcome", "sunshine", "princess",
    "shadow", "master", "hello123", "login", "passw0rd", "baseball",
    "freedom", "whatever", "trustno1", "superman", "batman", "abc123",
    "starwars",
]
DICT_TH = [
    "123456", "sawasdee", "thailand123", "rachada", "love@2024",
    "aomsin01", "bangkok55", "chang1990", "somchai99", "kanom1234",
]


@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Accel-Buffering"] = "no"
    return response


def payload() -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def password_from(data: dict[str, Any], key: str = "password") -> str:
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > 1024:
        raise ValueError("Password must be text with at most 1024 characters.")
    return value


def bcrypt_password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("bcrypt demo accepts passwords up to 72 UTF-8 bytes.")
    return encoded


def bcrypt_cost(data: dict[str, Any], default: int = 10) -> int:
    try:
        cost = int(data.get("cost", default))
    except (TypeError, ValueError):
        raise ValueError("Cost must be an integer from 4 to 12.") from None
    if not 4 <= cost <= 12:
        raise ValueError("Cost must be an integer from 4 to 12.")
    return cost


def event(kind: str, **values: Any) -> str:
    """Encode one newline-delimited JSON event for the live browser log."""
    return json.dumps({"type": kind, **values}, ensure_ascii=False) + "\n"


def stream_response(generator: Iterable[str]) -> Response:
    return Response(
        stream_with_context(generator),
        mimetype="application/x-ndjson",
        headers={"X-Accel-Buffering": "no"},
    )


@app.errorhandler(ValueError)
def bad_request(error: ValueError):
    return jsonify(error=str(error)), 400


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/wordlist/<wordlist_name>")
def get_wordlist(wordlist_name: str):
    wordlists = {"common": DICT_EN, "th": DICT_TH}
    words = wordlists.get(wordlist_name)
    if words is None:
        return jsonify(error="Unknown demonstration wordlist."), 404
    return jsonify(name=wordlist_name, count=len(words), words=words)


@app.post("/api/hash")
def hash_playground():
    data = payload()
    password = password_from(data)
    salt_text = data.get("salt", "")
    if not isinstance(salt_text, str) or len(salt_text) > 128:
        raise ValueError("Salt must be text with at most 128 characters.")
    cost = bcrypt_cost(data)
    bcrypt_input = bcrypt_password_bytes(password)

    def events():
        results = {}
        password_bytes = password.encode("utf-8")
        salt_bytes = salt_text.encode("utf-8")
        yield event("log", message="รับคำขอจากหน้าเว็บแล้ว เริ่มคำนวณใน Python")
        yield event("log", message=f"แปลง password เป็น UTF-8 bytes แล้ว ({len(password_bytes)} bytes); ไม่แสดงค่ารหัสผ่านใน log")
        yield event("log", message=f"salt ตัวอย่างมีความยาว {len(salt_bytes)} bytes")

        yield event("log", message=f"[1/3] ต่อ password bytes กับ salt bytes รวม {len(password_bytes + salt_bytes)} bytes แล้วคำนวณ MD5...")
        started = time.perf_counter()
        md5_digest = hashlib.md5((password + salt_text).encode("utf-8")).hexdigest()
        md5_ms = (time.perf_counter() - started) * 1000
        results["md5"] = {"hash": md5_digest, "milliseconds": md5_ms}
        yield event("log", message=f"MD5 เสร็จแล้ว: digest={md5_digest}; ใช้เวลา {md5_ms:.3f} ms")

        yield event("log", message="[2/3] ใช้ input bytes ชุดเดียวกันคำนวณ SHA-1...")
        started = time.perf_counter()
        sha1_digest = hashlib.sha1((password + salt_text).encode("utf-8")).hexdigest()
        sha1_ms = (time.perf_counter() - started) * 1000
        results["sha1"] = {"hash": sha1_digest, "milliseconds": sha1_ms}
        yield event("log", message=f"SHA-1 เสร็จแล้ว: digest={sha1_digest}; ใช้เวลา {sha1_ms:.3f} ms")

        yield event("log", message=f"[3/3] ขอ salt ใหม่จาก bcrypt (cost={cost}, work factor 2^{cost}={2**cost:,})...")
        bcrypt_salt = bcrypt.gensalt(rounds=cost)
        yield event("log", message=f"ได้ bcrypt salt: {bcrypt_salt.decode('ascii')}; เริ่ม key stretching")
        started = time.perf_counter()
        bcrypt_hash = bcrypt.hashpw(bcrypt_input, bcrypt_salt)
        bcrypt_ms = (time.perf_counter() - started) * 1000
        results["bcrypt"] = {"hash": bcrypt_hash.decode("ascii"), "milliseconds": bcrypt_ms}
        yield event("log", message=f"bcrypt เสร็จแล้ว: hash={bcrypt_hash.decode('ascii')}; ใช้เวลา {bcrypt_ms:.1f} ms")
        yield event("result", data=results)

    return stream_response(events())


@app.post("/api/dictionary")
def dictionary_attack():
    data = payload()
    target = password_from(data, "target")
    wordlist_name = data.get("wordlist", "common")
    if wordlist_name not in ("common", "th"):
        raise ValueError("Choose a supported demonstration wordlist.")
    cost = bcrypt_cost(data)
    bcrypt_target = bcrypt_password_bytes(target)
    words = DICT_EN if wordlist_name == "common" else DICT_TH

    def events():
        results = []
        yield event("log", message=f"เริ่ม Dictionary Attack: โหลด wordlist ตัวอย่าง {len(words)} คำ; เป้าหมายยาว {len(target.encode('utf-8'))} bytes")
        for algorithm in ("MD5", "SHA-1", "bcrypt"):
            found = None
            attempts = 0
            compute_seconds = 0.0
            yield event("log", message=f"เริ่มทดสอบ {algorithm}...")
            if algorithm == "bcrypt":
                target_hash = bcrypt.hashpw(bcrypt_target, bcrypt.gensalt(rounds=cost))
                yield event("log", message=f"สร้าง target bcrypt hash (cost={cost} / 2^{cost} work factor): {target_hash.decode('ascii')}")
                yield event("log", message="เริ่มตรวจ candidate ทีละคำด้วย bcrypt.checkpw; salt จาก target hash จะถูกใช้ตรวจอัตโนมัติ")
                for index, candidate in enumerate(words, start=1):
                    yield event("log", message=f"bcrypt attempt {index}/{len(words)}: candidate={candidate}; เรียก bcrypt.checkpw...")
                    started = time.perf_counter()
                    matched = bcrypt.checkpw(candidate.encode("utf-8"), target_hash)
                    compute_seconds += time.perf_counter() - started
                    attempts += 1
                    yield event("log", message=f"bcrypt attempt {index}: {'MATCH' if matched else 'mismatch'}")
                    if matched:
                        found = candidate
                        yield event("log", message=f"bcrypt พบคำที่ตรงกัน หลังลอง {attempts} ครั้ง")
                        break
            else:
                hash_fn = hashlib.md5 if algorithm == "MD5" else hashlib.sha1
                target_hash = hash_fn(target.encode("utf-8")).digest()
                yield event("log", message=f"สร้าง target {algorithm} digest: {target_hash.hex()}")
                for index, candidate in enumerate(words, start=1):
                    yield event("log", message=f"{algorithm} attempt {index}/{len(words)}: candidate={candidate}; hash candidate...")
                    started = time.perf_counter()
                    candidate_hash = hash_fn(candidate.encode("utf-8")).digest()
                    matched = candidate_hash == target_hash
                    compute_seconds += time.perf_counter() - started
                    attempts += 1
                    yield event("log", message=f"{algorithm} attempt {index}: digest={candidate_hash.hex()} → {'MATCH' if matched else 'mismatch'}")
                    if matched:
                        found = candidate
                        yield event("log", message=f"{algorithm} พบคำที่ตรงกัน หลังลอง {attempts} ครั้ง")
                        break

            elapsed_ms = compute_seconds * 1000
            result = {
                "algorithm": algorithm,
                "milliseconds": elapsed_ms,
                "attempts": attempts,
                "rate": attempts / max(compute_seconds, 0.000001),
                "found": found,
            }
            results.append(result)
            if not found:
                yield event("log", message=f"{algorithm} ลองครบ/หยุดที่ {attempts} คำ ไม่พบใน wordlist")
            yield event("progress", data=result)

        yield event("log", message="Dictionary Attack ทั้ง 3 วิธีเสร็จแล้ว")
        yield event("result", data={"word_count": len(words), "results": results})

    return stream_response(events())


@app.post("/api/bruteforce")
def brute_force():
    data = payload()
    target = password_from(data, "target")
    charset = data.get("charset", "abcdefghijklmnopqrstuvwxyz")
    if not isinstance(charset, str) or not charset or len(charset) > 128:
        raise ValueError("Choose a non-empty character set of at most 128 characters.")
    try:
        length = int(data.get("length", 3))
    except (TypeError, ValueError):
        raise ValueError("Length must be an integer from 1 to 10.") from None
    if not 1 <= length <= 10:
        raise ValueError("Length must be an integer from 1 to 10.")

    keyspace = len(charset) ** length

    def events():
        result = None
        yield event("log", message=f"Python เริ่ม brute-force ทดลอง: keyspace = {len(charset)}^{length} = {keyspace:,}")
        if length <= 4 and keyspace <= 2_000_000:
            target_hash = hashlib.md5(target.encode("utf-8")).digest()
            started = time.perf_counter()
            attempts = 0
            found = None
            detail_limit = 2_000
            progress_interval = max(1, keyspace // 20)
            yield event("log", message=f"สร้าง MD5 ของเป้าหมาย: {target_hash.hex()}")
            yield event("log", message=f"เริ่มไล่ candidate ตาม charset ({len(charset)} ตัว) ความยาว {length}; แสดงรายละเอียดราย candidate สูงสุด {detail_limit:,} รายการ")
            for chars in itertools.product(charset, repeat=length):
                candidate = "".join(chars)
                attempts += 1
                candidate_hash = hashlib.md5(candidate.encode("utf-8")).digest()
                matched = candidate_hash == target_hash
                if attempts <= detail_limit:
                    yield event("log", message=f"attempt {attempts:,}: candidate={candidate!r}; MD5={candidate_hash.hex()} → {'MATCH' if matched else 'mismatch'}")
                elif attempts == detail_limit + 1:
                    yield event("log", message=f"ถึงขีดจำกัดรายละเอียด {detail_limit:,} รายการแล้ว; ต่อจากนี้แสดงความคืบหน้าเป็นช่วง")
                if matched:
                    found = candidate
                    yield event("log", message=f"พบ candidate ตรงกันหลังลอง {attempts:,} ครั้ง")
                    break
                if attempts % progress_interval == 0 and attempts > detail_limit:
                    percent = attempts / keyspace * 100
                    yield event("log", message=f"ความคืบหน้า: {attempts:,} / {keyspace:,} candidates ({percent:.1f}%)")
            elapsed_ms = (time.perf_counter() - started) * 1000
            elapsed_seconds = max(elapsed_ms / 1000, 0.000001)
            result = {
                "attempts": attempts,
                "milliseconds": elapsed_ms,
                "rate": attempts / elapsed_seconds,
                "found": found,
            }
            if not found:
                yield event("log", message=f"ลองครบ {attempts:,} ครั้งแล้ว ไม่พบในขอบเขตนี้")
            yield event("progress", data=result)
        else:
            yield event("log", message="keyspace ใหญ่เกินขอบเขตทดลองจริง จึงข้ามการไล่ candidate และคำนวณเฉพาะค่าประมาณ")

        average_guesses = keyspace / 2
        estimates = {
            "MD5": average_guesses / 20_000_000_000,
            "SHA-1": average_guesses / 8_000_000_000,
            "bcrypt (cost 12)": average_guesses / 15_000,
        }
        yield event("log", message="คำนวณเวลาเฉลี่ยโดยประมาณจากครึ่งหนึ่งของ keyspace")
        yield event("result", data={"keyspace": keyspace, "real_result": result, "estimated_seconds": estimates})

    return stream_response(events())


@app.post("/api/salt-demo")
def salt_demo():
    data = payload()
    password = password_from(data)
    cost = bcrypt_cost(data)
    password_bytes = bcrypt_password_bytes(password)

    def events():
        examples = []
        yield event("log", message=f"เริ่มสร้าง bcrypt hash 3 รอบ; password input={len(password_bytes)} UTF-8 bytes; cost={cost} (2^{cost} work factor)")
        for index in range(1, 4):
            yield event("log", message=f"รอบ {index}/3: สุ่ม salt ใหม่ แล้วคำนวณ bcrypt...")
            salt = bcrypt.gensalt(rounds=cost)
            yield event("log", message=f"รอบ {index}/3: ได้ salt={salt.decode('ascii')}; ส่ง password bytes และ salt เข้า bcrypt")
            hashed = bcrypt.hashpw(password_bytes, salt)
            example = {"salt": salt.decode("ascii"), "hash": hashed.decode("ascii")}
            examples.append(example)
            yield event("log", message=f"รอบ {index}/3: hash={example['hash']}")
            yield event("progress", data={"index": index, **example})
            yield event("log", message=f"รอบ {index}/3 เสร็จแล้ว; บันทึก salt และ hash ที่ได้")
        yield event("result", data={"examples": examples})

    return stream_response(events())


if __name__ == "__main__":
    # Bind to localhost: this is a classroom demo server, not a production service.
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
