$ErrorActionPreference = 'Stop'
$nativeRoot = Join-Path $PSScriptRoot '..\.native'
$buildName = 'ffmpeg-n9.0-latest-win64-lgpl-shared-9.0'
$ffmpegRoot = Join-Path $nativeRoot $buildName
if (-not (Test-Path -LiteralPath (Join-Path $ffmpegRoot 'include\libavcodec\avcodec.h'))) {
    New-Item -ItemType Directory -Path $nativeRoot -Force | Out-Null
    $archive = Join-Path $nativeRoot 'ffmpeg.zip'
    Invoke-WebRequest "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/$buildName.zip" -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $nativeRoot -Force
}
$env:FFMPEG_DIR = (Resolve-Path -LiteralPath $ffmpegRoot).Path
$env:LIBCLANG_PATH = 'C:\Program Files\LLVM\bin'
$env:PATH = "$env:FFMPEG_DIR\bin;$env:PATH"
if ($env:GITHUB_ENV) {
    "FFMPEG_DIR=$env:FFMPEG_DIR" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
    "LIBCLANG_PATH=$env:LIBCLANG_PATH" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
    "$env:FFMPEG_DIR\bin" | Out-File -FilePath $env:GITHUB_PATH -Append -Encoding utf8
}
