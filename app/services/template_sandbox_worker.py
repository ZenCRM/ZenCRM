"""Standalone, resource-limited renderer. Never imports the Flask application."""
import os
import sys
import json

MAX_MEMORY = 128 * 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024
MAX_INPUT = 4 * 1024 * 1024


def limit_resources():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes

        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('min_working_set', ctypes.c_size_t),
                ('max_working_set', ctypes.c_size_t), ('active_processes', wintypes.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]

        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                ('job_memory', ctypes.c_size_t), ('peak_process_memory', ctypes.c_size_t),
                ('peak_job_memory', ctypes.c_size_t)]

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.SetInformationJobObject.restype = wintypes.BOOL
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        limits = Extended()
        limits.basic.flags = 0x100 | 0x2  # PROCESS_MEMORY | PROCESS_TIME
        limits.basic.process_time = 2 * 10_000_000  # 100 ns units
        limits.process_memory = MAX_MEMORY
        job = kernel.CreateJobObjectW(None, None)
        if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise RuntimeError('Could not apply render resource limits')
        if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            raise RuntimeError('Could not isolate render process')
        # Keep the job open until process exit.
        return job
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))


def main():
    job = limit_resources()
    from jinja2.sandbox import SandboxedEnvironment
    from jinja2.exceptions import SecurityError
    request = json.loads(sys.stdin.buffer.read(MAX_INPUT + 1))
    content = request['content']
    if not isinstance(content, str) or len(content) > 1_000_000:
        raise ValueError('Template input limit exceeded')
    env = SandboxedEnvironment(autoescape=True)
    try:
        if request.get('validate'):
            env.parse(content)
            return {'result': ''}
        chunks, size = [], 0
        for chunk in env.from_string(content).generate(**request.get('context', {})):
            size += len(chunk.encode('utf-8'))
            if size > MAX_OUTPUT:
                raise ValueError('Rendered template exceeds 2 MiB')
            chunks.append(chunk)
        return {'result': ''.join(chunks)}
    except SecurityError:
        return {'security_error': True}


if __name__ == '__main__':
    try:
        answer = main()
    except Exception:
        answer = {'error': True}
    sys.stdout.buffer.write(json.dumps(answer, ensure_ascii=False).encode('utf-8'))
