# GOG startup

The reported load failure is not reproduced locally. Compilation and available
Address Library IDs do not prove live hook compatibility.

For GOG 1.6.1179, use SKSE 2.2.6 GOG, the 1.6.x Address Library including
`versionlib-1-6-1179-0.bin`, a matching Menu Framework 3 build and the x64 Visual C++
runtime. A missing C++ runtime is a possible cause, not a confirmed diagnosis.

Check skse64.log for DLL errors, then Walk With Me.log for runtime, hooks and menu
registration. An absent mod log points to failure before logger startup. Supply
the affected runtime and logs; do not substitute Steam offsets.
