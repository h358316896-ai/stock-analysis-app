Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Start a simple HTTP server to serve the HTML file
$htmlPath = "C:\Users\五颜六色\stock-analysis-app-main\video-ad.html"
$outputPath = "C:\Users\五颜六色\stock-analysis-app-main\video-ad-screenshot.png"

# Create a listener on a random port
$listener = [System.Net.HttpListener]::new()
$port = 8765
$listener.Prefixes.Add("http://localhost:$port/")
$listener.Start()

# Serve the HTML file in background
$serverJob = Start-Job -ScriptBlock {
    param($path, $port)
    $l = [System.Net.HttpListener]::new()
    $l.Prefixes.Add("http://localhost:$port/")
    $l.Start()
    while ($true) {
        $ctx = $l.GetContext()
        $file = [System.IO.File]::ReadAllText($path)
        $buf = [System.Text.Encoding]::UTF8.GetBytes($file)
        $ctx.Response.ContentType = "text/html; charset=utf-8"
        $ctx.Response.OutputStream.Write($buf, 0, $buf.Length)
        $ctx.Response.Close()
    }
} -ArgumentList $htmlPath, $port

Start-Sleep -Seconds 1

# Use WebBrowser control to render and capture
$wb = New-Object System.Windows.Forms.WebBrowser
$wb.Width = 1080
$wb.Height = 1920
$wb.ScrollBarsEnabled = $false
$wb.ScriptErrorsSuppressed = $true
$wb.Navigate("http://localhost:$port/")

# Wait for page to load
while ($wb.ReadyState -ne 'Complete') {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 100
}
Start-Sleep -Seconds 2

# Take screenshot
$bitmap = New-Object System.Drawing.Bitmap 1080, 1920
$wb.DrawToBitmap($bitmap, (New-Object System.Drawing.Rectangle 0, 0, 1080, 1920))
$bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()

$listener.Stop()
Stop-Job -Job $serverJob

Write-Output "Screenshot saved to: $outputPath"
