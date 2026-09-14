# Publish source

Create an empty public GitHub repo named `Walk-With-Me`. Do not add a README or license there.

In PowerShell:

```powershell
Set-Location -LiteralPath 'X:\!--- Main\Documents\Nolvus\Wayfarer'
git status --short
git add .
git diff --cached --stat
```

Review the files. This includes earlier uncommitted changes. Then replace YOUR-USERNAME:

```powershell
git commit -m "Prepare source release"
git remote add origin https://github.com/YOUR-USERNAME/Walk-With-Me.git
git push -u origin main
```

If origin already exists, check `git remote -v` and use the correct remote.

Create a GitHub Release. Attach the mod ZIP, complete Source.zip and both checksum
files from `release/source-review`. Link that source download on the mod page.
GitHub's automatic source ZIP does not include the ignored dependency sources.
Keep each complete source ZIP with its matching DLL version.

After uploading, send moderators the links and ask them to review the corrected
license and source files. If the takedown covers an older DLL, provide its matching
source too. The host decides whether to restore the page.
