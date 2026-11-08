/* SDL3 ABI shim: untouched functions forward to the official SDL3-real.dll.
 * Only motor output and controller-open diagnostics are intercepted. */
#include <windows.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static HMODULE self_module;
static INIT_ONCE once = INIT_ONCE_STATIC_INIT;
static HMODULE real_module;
static int scale = 100;
static LONG calls, failures;
static CRITICAL_SECTION log_lock;
static char log_path[32768];

static BOOL CALLBACK initialize(PINIT_ONCE ignored, PVOID arg, PVOID *context) {
    (void)ignored; (void)arg; (void)context;
    char path[32768];
    GetModuleFileNameA(self_module, path, sizeof path);
    char *end = strrchr(path, '\\');
    if (!end) return FALSE;
    strcpy(end + 1, "SDL3-real.dll");
    real_module = LoadLibraryA(path);
    if (!real_module) return FALSE;
    char *value = getenv("BB_RUMBLE_PERCENT");
    if (value && *value) { scale = atoi(value); if (scale < 0) scale = 0; if (scale > 100) scale = 100; }
    const char *custom = getenv("BB_USER_DIR");
    if (custom && *custom) snprintf(log_path, sizeof log_path, "%s\\rumble.log", custom);
    else {
        *end = 0;
        char *parent = strrchr(path, '\\');
        if (!parent) return FALSE;
        *parent = 0;
        snprintf(log_path, sizeof log_path, "%s\\user\\rumble.log", path);
    }
    InitializeCriticalSection(&log_lock);
    return TRUE;
}
static void log_line(const char *message) {
    EnterCriticalSection(&log_lock);
    FILE *f = fopen(log_path, "ab");
    if (f) { fprintf(f, "pid=%lu tick=%llu %s\n", GetCurrentProcessId(), GetTickCount64(), message); fclose(f); }
    LeaveCriticalSection(&log_lock);
}
void *SDL_OpenGamepad(uint32_t id) {
    if (!InitOnceExecuteOnce(&once, initialize, NULL, NULL)) return NULL;
    void *(*open_pad)(uint32_t) = (void *)GetProcAddress(real_module, "SDL_OpenGamepad");
    const char *(*name)(void *) = (void *)GetProcAddress(real_module, "SDL_GetGamepadName");
    uint32_t (*properties)(void *) = (void *)GetProcAddress(real_module, "SDL_GetGamepadProperties");
    bool (*property)(uint32_t, const char *, bool) = (void *)GetProcAddress(real_module, "SDL_GetBooleanProperty");
    const char *(*error)(void) = (void *)GetProcAddress(real_module, "SDL_GetError");
    void *pad = open_pad(id);
    char message[2048];
    snprintf(message, sizeof message, "open id=%u name=%s rumble_supported=%d strength=%d%% error=%s", id,
             pad ? name(pad) : "none", pad ? property(properties(pad), "SDL.joystick.cap.rumble", false) : 0,
             scale, pad ? "" : error());
    log_line(message);
    return pad;
}
bool SDL_RumbleGamepad(void *pad, uint16_t low, uint16_t high, uint32_t ms) {
    if (!InitOnceExecuteOnce(&once, initialize, NULL, NULL)) return false;
    bool (*rumble)(void *, uint16_t, uint16_t, uint32_t) = (void *)GetProcAddress(real_module, "SDL_RumbleGamepad");
    const char *(*error)(void) = (void *)GetProcAddress(real_module, "SDL_GetError");
    const uint16_t out_low = (uint16_t)((uint32_t)low * scale / 100);
    const uint16_t out_high = (uint16_t)((uint32_t)high * scale / 100);
    bool ok = rumble(pad, out_low, out_high, ms);
    LONG count = InterlockedIncrement(&calls);
    LONG failed = ok ? 0 : InterlockedIncrement(&failures);
    if (count <= 20 || count % 300 == 0 || (failed && (failed <= 10 || failed % 300 == 0))) {
        char message[2048];
        snprintf(message, sizeof message, "call=%ld input=%u,%u output=%u,%u duration_ms=%u success=%d failures=%ld error=%s",
                 count, low, high, out_low, out_high, ms, ok, failures, ok ? "" : error());
        log_line(message);
    }
    return ok;
}
BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) { self_module = instance; DisableThreadLibraryCalls(instance); }
    return TRUE;
}
