# TipJar GitHub Update Script
# Created for easy repository updates

# Get current timestamp for default commit message
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Function to show script header
function Show-Header {
    Write-Host "`n==================================" -ForegroundColor Green
    Write-Host "    TipJar GitHub Update Tool     " -ForegroundColor Green
    Write-Host "==================================`n" -ForegroundColor Green
}

# Function to get optional commit message from user
function Get-CommitMessage {
    Write-Host "Current changes to be committed:" -ForegroundColor Cyan
    git status --short
    Write-Host "`nEnter commit message (press Enter for default timestamp message):" -ForegroundColor Yellow
    $message = Read-Host
    
    if ([string]::IsNullOrWhiteSpace($message)) {
        $message = "Update TipJar app - $timestamp"
    }
    
    return $message
}

# Main script
Show-Header

# Check if we're in a git repository
if (-not (Test-Path -Path ".git")) {
    Write-Host "Error: Not in a Git repository. Please run this script from your TipJar project folder." -ForegroundColor Red
    exit 1
}

# Check for changes
$changes = git status --porcelain
if ([string]::IsNullOrWhiteSpace($changes)) {
    Write-Host "No changes detected in the repository." -ForegroundColor Yellow
    $continue = Read-Host "Do you want to continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 0
    }
}

try {
    # Step 1: Add all files
    Write-Host "Adding all changes..." -ForegroundColor Cyan
    git add .
    
    # Step 2: Commit changes
    $commitMessage = Get-CommitMessage
    Write-Host "Committing with message: $commitMessage" -ForegroundColor Cyan
    git commit -m "$commitMessage"
    
    # Step 3: Push to GitHub
    Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
    git push origin main
    
    # Success message
    Write-Host "`nSuccess! All changes have been pushed to GitHub." -ForegroundColor Green
    Write-Host "Your Streamlit app will automatically update with these changes." -ForegroundColor Green
}
catch {
    # Error handling
    Write-Host "`nError occurred during the update process:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nPlease resolve the issue and try again." -ForegroundColor Yellow
}

# End of script
Write-Host "`nPress any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 