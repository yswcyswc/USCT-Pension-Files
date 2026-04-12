Get-ChildItem page-*.png | ForEach-Object {
    $n = [int]($_.BaseName -replace 'page-','')
    Rename-Item $_ -NewName ("Robinson_Lucius-$n.png")
}