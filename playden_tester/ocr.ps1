# Windows' built-in OCR (Windows.Media.Ocr) on one image; prints JSON lines: {"text", "x", "y", "w", "h"} per line.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File ocr.ps1 <image>
param([Parameter(Mandatory = $true)][string]$Path)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1"
})[0]
function Await($operation, [Type]$type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
    $task.Wait() | Out-Null
    $task.Result
}
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $Path).Path)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { throw "no OCR language installed" }
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
foreach ($line in $result.Lines) {
    $xs = $line.Words | ForEach-Object { $_.BoundingRect.X }
    $ys = $line.Words | ForEach-Object { $_.BoundingRect.Y }
    $x2 = $line.Words | ForEach-Object { $_.BoundingRect.X + $_.BoundingRect.Width }
    $y2 = $line.Words | ForEach-Object { $_.BoundingRect.Y + $_.BoundingRect.Height }
    $x = ($xs | Measure-Object -Minimum).Minimum
    $y = ($ys | Measure-Object -Minimum).Minimum
    [pscustomobject]@{ text = $line.Text; x = [int]$x; y = [int]$y
        w = [int](($x2 | Measure-Object -Maximum).Maximum - $x); h = [int](($y2 | Measure-Object -Maximum).Maximum - $y) } |
        ConvertTo-Json -Compress
}
