/* Standalone SDL test. --probe never sends a motor command. */
#include <windows.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    char path[32768];
    GetModuleFileNameA(NULL, path, sizeof path);
    strcpy(strrchr(path, '\\') + 1, "SDL3.dll");
    HMODULE dll = LoadLibraryA(path);
    if (!dll) { puts("Cannot load SDL3.dll"); return 1; }
#define LOAD(ret, name, args) ret (*name) args = (void *)GetProcAddress(dll, #name)
    LOAD(bool, SDL_Init, (uint32_t));
    LOAD(void, SDL_Quit, (void));
    LOAD(void, SDL_PumpEvents, (void));
    LOAD(uint32_t *, SDL_GetGamepads, (int *));
    LOAD(void *, SDL_OpenGamepad, (uint32_t));
    LOAD(const char *, SDL_GetGamepadName, (void *));
    LOAD(bool, SDL_RumbleGamepad, (void *, uint16_t, uint16_t, uint32_t));
    LOAD(const char *, SDL_GetError, (void));
    LOAD(void, SDL_CloseGamepad, (void *));
    LOAD(void, SDL_free, (void *));
    if (!SDL_Init(0x2000)) { printf("SDL_Init: %s\n", SDL_GetError()); return 1; }
    for (int i = 0; i < 20; ++i) { SDL_PumpEvents(); Sleep(10); }
    int count = 0;
    uint32_t *ids = SDL_GetGamepads(&count);
    printf("controllers=%d\n", count);
    int result = count ? 0 : 2;
    void *pad = count ? SDL_OpenGamepad(ids[0]) : NULL;
    SDL_free(ids);
    if (count && !pad) { printf("Open failed: %s\n", SDL_GetError()); result = 1; }
    if (pad) {
        printf("controller=%s\n", SDL_GetGamepadName(pad));
        if (argc < 2 || strcmp(argv[1], "--probe")) {
            uint16_t motors[3][2] = {{40000, 0}, {0, 40000}, {40000, 40000}};
            for (int i = 0; i < 3; ++i) {
                bool ok = SDL_RumbleGamepad(pad, motors[i][0], motors[i][1], 250);
                printf("test=%d success=%d error=%s\n", i + 1, ok, ok ? "" : SDL_GetError());
                if (!ok) result = 1;
                for (int j = 0; j < 35; ++j) { SDL_PumpEvents(); Sleep(10); }
            }
            SDL_RumbleGamepad(pad, 0, 0, 0);
        }
        SDL_CloseGamepad(pad);
    }
    SDL_Quit();
    return result;
}
