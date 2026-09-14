param(
    [string]$Vcpkg = 'X:\vcpkg\vcpkg.exe',
    [string]$CMake = 'X:\VisualStudio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
$source = Join-Path $root 'build/deps/CommonLibSSE-NG-7.5.1'
$installed = Join-Path $root 'build/deps/vcpkg-7.5.1'
$build = Join-Path $root 'build/modern'
if (-not (Test-Path -LiteralPath $source)) {
    git clone --depth 1 --branch v7.5.1 https://github.com/alandtse/CommonLibSSE-NG.git $source
    if ($LASTEXITCODE -ne 0) { throw 'CommonLib download failed' }
}
$revision = git -C $source rev-parse HEAD
if ($revision -ne 'bedcb1e05418baba7b316a650b6180c2dd6007a8') { throw 'Unexpected CommonLib revision' }
& $Vcpkg install "--x-manifest-root=$source" "--x-install-root=$installed" --triplet=x64-windows-static-md --x-no-default-features
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
$prefix = Join-Path $installed 'x64-windows-static-md'
& $CMake -S $root -B $build -G 'Visual Studio 17 2022' -A x64 "-DWAYFARER_COMMONLIB_SOURCE=$source" "-DCMAKE_PREFIX_PATH=$prefix" "-DSIMPLEINI_INCLUDE_DIRS=$prefix/include" -DBUILD_TESTS=OFF -DENABLE_SKYRIM_SE=ON -DENABLE_SKYRIM_AE=ON -DENABLE_SKYRIM_VR=OFF -DSKSE_SUPPORT_XBYAK=ON -DSKSE_SUPPORT_PATCH_SAFETY=OFF -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL
if ($LASTEXITCODE -ne 0) { throw 'Compatibility configuration failed' }
& $CMake --build $build --config Release --parallel 8
if ($LASTEXITCODE -ne 0) { throw 'Compatibility build failed' }
& (Join-Path (Split-Path $CMake) 'ctest.exe') --test-dir $build -C Release --output-on-failure
if ($LASTEXITCODE -ne 0) { throw 'Compatibility tests failed' }
Write-Output "Compatibility DLL: $build/bin/Release/Wayfarer.dll"
