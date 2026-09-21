/* Native Windows launcher for the stand-alone himena bundle.
 *
 * It runs the bundled interpreter as ``python(w).exe -m himena <args>`` so
 * that Windows sees a real ``himena.exe`` (in "Open with", the Task Manager,
 * file associations, ...) instead of ``python.exe``. installer/build.py
 * compiles this file twice:
 *
 * - ``{app}\himena.exe``     GUI subsystem, runs ``{app}\python\pythonw.exe``
 * - ``{app}\bin\himena.exe`` console subsystem (HIMENA_CONSOLE defined), runs
 *                            ``{app}\python\python.exe`` so that ``himena
 *                            --version`` etc. print to the terminal.
 *
 * The command-line arguments are forwarded verbatim (quoting included).
 */
#include <windows.h>

#ifdef HIMENA_CONSOLE
#define PYTHON_REL L"\\..\\python\\python.exe"
#else
#define PYTHON_REL L"\\python\\pythonw.exe"
#endif

/* CreateProcessW accepts at most 32767 characters in the command line. */
#define CMDLINE_MAX 32768

static wchar_t g_python[CMDLINE_MAX];
static wchar_t g_cmdline[CMDLINE_MAX];

static void report_error(const wchar_t *what, DWORD code)
{
    static wchar_t msg[CMDLINE_MAX + 128];
    wsprintfW(msg, L"%s (error %lu):\n%s", what, (unsigned long)code, g_python);
#ifdef HIMENA_CONSOLE
    HANDLE err = GetStdHandle(STD_ERROR_HANDLE);
    DWORD written;
    lstrcatW(msg, L"\n");
    WriteConsoleW(err, msg, lstrlenW(msg), &written, NULL);
#else
    MessageBoxW(NULL, msg, L"himena", MB_OK | MB_ICONERROR);
#endif
}

/* Skip the first (program name) token of a raw command line. */
static const wchar_t *skip_program_name(const wchar_t *cmd)
{
    if (*cmd == L'"') {
        cmd++;
        while (*cmd && *cmd != L'"')
            cmd++;
        if (*cmd == L'"')
            cmd++;
    } else {
        while (*cmd && *cmd != L' ' && *cmd != L'\t')
            cmd++;
    }
    while (*cmd == L' ' || *cmd == L'\t')
        cmd++;
    return cmd;
}

static int launch(void)
{
    DWORD n = GetModuleFileNameW(NULL, g_python, CMDLINE_MAX);
    if (n == 0 || n >= CMDLINE_MAX) {
        report_error(L"Could not locate the himena launcher", GetLastError());
        return 1;
    }
    /* strip "\himena.exe" and append the relative path of the interpreter */
    while (n > 0 && g_python[n - 1] != L'\\')
        n--;
    if (n > 0)
        n--;
    g_python[n] = L'\0';
    lstrcatW(g_python, PYTHON_REL);

    const wchar_t *args = skip_program_name(GetCommandLineW());
    if ((DWORD)(lstrlenW(g_python) + lstrlenW(args) + 16) >= CMDLINE_MAX) {
        report_error(L"Command line is too long", 0);
        return 1;
    }
    lstrcpyW(g_cmdline, L"\"");
    lstrcatW(g_cmdline, g_python);
    lstrcatW(g_cmdline, L"\" -m himena");
    if (*args) {
        lstrcatW(g_cmdline, L" ");
        lstrcatW(g_cmdline, args);
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    if (!CreateProcessW(g_python, g_cmdline, NULL, NULL, TRUE, 0, NULL, NULL,
                        &si, &pi)) {
        report_error(L"Could not start the bundled Python interpreter",
                     GetLastError());
        return 1;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    return (int)code;
}

#ifdef HIMENA_CONSOLE
int wmain(void)
{
    /* let Ctrl+C reach the interpreter instead of killing this launcher */
    SetConsoleCtrlHandler(NULL, TRUE);
    return launch();
}
#else
int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                    PWSTR pCmdLine, int nCmdShow)
{
    (void)hInstance;
    (void)hPrevInstance;
    (void)pCmdLine;
    (void)nCmdShow;
    return launch();
}
#endif
