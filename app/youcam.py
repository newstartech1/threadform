"""Official YouCam Clothes V4 integration, without emulation or fake outputs."""
from __future__ import annotations

import os
from urllib.parse import urlsplit
import requests

BASE = os.getenv('YOUCAM_API_BASE', 'https://yce-api-01.makeupar.com').rstrip('/')
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class YouCamError(Exception):
    pass


def api_key():
    key = os.getenv('YOUCAM_API_KEY', '').strip()
    if not key:
        raise YouCamError('YOUCAM_API_KEY is not configured on the server.')
    return key


def base_url():
    parsed = urlsplit(BASE)
    # Restrict to an official Perfect Corp domain: cannot use arbitrary URLs.
    if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.makeupar.com'):
        raise YouCamError('Invalid YOUCAM_API_BASE; use an official makeupar.com HTTPS endpoint.')
    return BASE


def headers():
    return {'Authorization': f'Bearer {api_key()}', 'Content-Type': 'application/json'}


def verify_upload_bytes(content: bytes, filename: str):
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise YouCamError('Upload a JPEG or PNG smaller than 8 MB.')
    from PIL import Image
    from io import BytesIO
    try:
        im = Image.open(BytesIO(content))
        im.verify()
    except Exception as exc:
        raise YouCamError('Invalid image file.') from exc
    ext = (filename or '').lower().rsplit('.', 1)[-1]
    if ext not in ('jpg', 'jpeg', 'png'):
        raise YouCamError('Only JPEG and PNG are supported.')
    return 'image/png' if ext == 'png' else 'image/jpg'


def check_provider_response(response):
    try:
        data = response.json()
    except ValueError as exc:
        raise YouCamError(f'YouCam sent an invalid response (HTTP {response.status_code}).') from exc
    if response.status_code >= 400 or data.get('status', 200) >= 400:
        msg = data.get('error') or data.get('message') or data.get('error_code') or 'Provider error'
        raise YouCamError(f'YouCam rejected the request (HTTP {response.status_code}): {str(msg)[:220]}')
    return data.get('data') or {}


def upload_image(content: bytes, filename: str) -> str:
    content_type = verify_upload_bytes(content, filename)
    safe_name = 'garment.png' if content_type == 'image/png' else 'garment.jpg'
    payload = {'files': [{'content_type': content_type, 'file_name': safe_name, 'file_size': len(content)}]}
    try:
        preflight = requests.post(f'{base_url()}/s2s/v2.0/file', headers=headers(), json=payload, timeout=25)
        result = check_provider_response(preflight)
        record = result['files'][0]
        upload = record['requests'][0]
        dest = urlsplit(upload['url'])
        # Presigned uploads should go to S3/AWS; never follow arbitrary/provider-supplied hosts.
        host = dest.hostname or ''
        if dest.scheme != 'https' or not (host.endswith('.amazonaws.com') or host.endswith('.amazonaws.com.cn')):
            raise YouCamError('Provider returned an unexpected upload URL host.')
        supplied = upload.get('headers') or {}
        put_headers = {'Content-Type': content_type, 'Content-Length': str(len(content))}
        for k, v in supplied.items():
            if k.lower() in ('content-type', 'content-length'):
                put_headers[k] = v
        resp = requests.put(upload['url'], data=content, headers=put_headers, timeout=45, allow_redirects=False)
        if resp.status_code not in (200, 201, 204):
            raise YouCamError(f'The image upload failed (HTTP {resp.status_code}).')
        return record['file_id']
    except (KeyError, IndexError, TypeError) as exc:
        raise YouCamError('Unexpected response structure from YouCam file upload API.') from exc
    except requests.RequestException as exc:
        raise YouCamError(f'Unable to reach YouCam upload API: {str(exc)[:140]}') from exc


def create_tryon(person: bytes, person_name: str, garment: bytes, garment_name: str, category='upper_body'):
    if category not in ('upper_body', 'lower_body', 'full_body', 'outer', 'auto'):
        raise YouCamError('Unsupported garment category.')
    src_id = upload_image(person, person_name)
    ref_id = upload_image(garment, garment_name)
    try:
        resp = requests.post(f'{base_url()}/s2s/v2.0/task/cloth-v4', headers=headers(),
                             json={'src_file_id': src_id, 'ref_file_id': ref_id,
                                   'garment_category': category, 'filter_multi_person': 'normal'}, timeout=30)
        data = check_provider_response(resp)
        task = data.get('task_id')
        if not isinstance(task, str) or not task:
            raise YouCamError('The provider did not return a task ID.')
        return task
    except requests.RequestException as exc:
        raise YouCamError(f'Unable to create YouCam task: {str(exc)[:140]}') from exc


def poll_tryon(task_id: str):
    try:
        resp = requests.get(f'{base_url()}/s2s/v2.0/task/cloth-v4/{task_id}', headers=headers(), timeout=25)
        data = check_provider_response(resp)
    except requests.RequestException as exc:
        raise YouCamError(f'Unable to check YouCam task: {str(exc)[:140]}') from exc
    status = data.get('task_status', 'unknown')
    # The image URL is returned unmodified from the provider; it is time-limited.
    results = data.get('results') or {}
    url = results.get('url') if isinstance(results, dict) else None
    return {'status': status, 'image_url': url if status == 'success' else None,
            'message': str(data.get('error') or data.get('failure_reason') or '')[:240]}
