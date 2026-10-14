param([string]$MayaUserDirectory)
$ErrorActionPreference = 'Stop'
if (-not $MayaUserDirectory) {
    $MayaUserDirectory = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'maya'
}
$mayaRoot = [IO.Path]::GetFullPath($MayaUserDirectory)
$sourceRoot = $PSScriptRoot
$required = @('rigitnow.py', 'rigitnow_plugin.py', 'reference_template.json', 'icons\rigiitnow_icon.png')
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $relative) -PathType Leaf)) {
        throw "Missing installation file: $relative"
    }
}
$modules = Join-Path $mayaRoot 'modules'
$package = Join-Path $modules 'rigitnow'
$scripts = Join-Path $package 'scripts'
$plugins = Join-Path $package 'plug-ins'
$packageIcons = Join-Path $package 'icons'
foreach ($directory in @($modules, $scripts, $plugins, $packageIcons)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
Copy-Item -LiteralPath (Join-Path $sourceRoot 'rigitnow.py') -Destination $scripts -Force
Copy-Item -LiteralPath (Join-Path $sourceRoot 'reference_template.json') -Destination $scripts -Force
Copy-Item -LiteralPath (Join-Path $sourceRoot 'rigitnow_plugin.py') -Destination $plugins -Force
$iconSource = Join-Path $sourceRoot 'icons\rigiitnow_icon.png'
Copy-Item -LiteralPath $iconSource -Destination $packageIcons -Force
# Shared icons plus every existing Maya version's user icons directory.
$iconDirectories = @((Join-Path $mayaRoot 'icons'))
foreach ($version in Get-ChildItem -LiteralPath $mayaRoot -Directory) {
    if ($version.Name -match '^\d{4}(?:[-._].*)?$') {
        $iconDirectories += Join-Path $version.FullName 'prefs\icons'
    }
}
foreach ($directory in $iconDirectories) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    Copy-Item -LiteralPath $iconSource -Destination $directory -Force
}
$moduleDefinition = @(
    '+ rigitnow 1.0.0 ./rigitnow'
    'PYTHONPATH +:= scripts'
    'MAYA_PLUG_IN_PATH +:= plug-ins'
    'XBMLANGPATH +:= icons'
) -join "`r`n"
[IO.File]::WriteAllText((Join-Path $modules 'rigitnow.mod'), $moduleDefinition + "`r`n", [Text.Encoding]::ASCII)
Write-Host 'rigitnow plugin, rigging module, template, and shelf icon installed.'
Write-Host 'Restart Maya, load rigitnow_plugin.py in Plug-in Manager, and enable Auto load.'
Write-Host 'Loading the plugin creates or updates the rigitnow shelf button.'
