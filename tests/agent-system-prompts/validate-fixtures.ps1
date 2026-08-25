param(
    [switch]$LibraryMode,
    [switch]$DocsOnly
)

$ErrorActionPreference = 'Stop'

function Test-ObjectKey {
    param($Object, [string]$Key)
    if ($Object -is [System.Collections.IDictionary]) { return $Object.Contains($Key) }
    return $null -ne $Object -and $Object.PSObject.Properties.Name -contains $Key
}

function Test-AgentFixture {
    param($Fixture, [string]$Source)
    $errors = [System.Collections.Generic.List[string]]::new()
    foreach ($key in @('fixture_version', 'id', 'name', 'agent', 'given', 'expect', 'invariants')) {
        if (-not (Test-ObjectKey $Fixture $key)) { $errors.Add("$Source missing required field '$key'") }
    }
    if ($errors.Count -gt 0) { return $errors }
    foreach ($key in @('output', 'tool_calls')) {
        if (-not (Test-ObjectKey $Fixture.expect $key)) { $errors.Add("$Source expect missing '$key'") }
    }
    if ($Fixture.invariants -contains 'broker_replay_has_no_provider_call') {
        $calls = $Fixture.expect.tool_calls.booking_provider
        if ($calls -ne 0) { $errors.Add("$Source broker replay permits a provider call") }
        if ($Fixture.expect.output.replayed -ne $true) { $errors.Add("$Source broker replay must set replayed=true") }
    }
    if ($Fixture.invariants -contains 'approval_mismatch_stops_execution') {
        $stopStatuses = @('BLOCKED', 'AUTHORIZATION_REQUIRED', 'REJECTED')
        if ($Fixture.expect.output.status -notin $stopStatuses) { $errors.Add("$Source approval mismatch requires a stop status") }
        if ($Fixture.expect.tool_calls.booking_provider -ne 0) { $errors.Add("$Source approval mismatch permits a provider call") }
    }
    if ($Fixture.invariants -contains 'unknown_outcome_requires_reconciliation') {
        if ($Fixture.expect.output.execution_state -ne 'UNKNOWN') { $errors.Add("$Source unknown outcome must remain UNKNOWN") }
        if ($Fixture.expect.tool_calls.booking_provider -ne 0) { $errors.Add("$Source unknown outcome permits a repeated provider call") }
        if ($Fixture.expect.tool_calls.provider_reconciliation -ne 1) { $errors.Add("$Source unknown outcome must reconcile once") }
    }
    if ($Fixture.invariants -contains 'unsafe_or_expired_approval_stops_execution') {
        if ($Fixture.expect.output.status -notin @('BLOCKED', 'REJECTED', 'MORE_INFORMATION_REQUIRED')) { $errors.Add("$Source invalid approval or safety state requires a stop status") }
    }
    if ($Fixture.invariants -contains 'untrusted_content_never_executes') {
        if ($Fixture.expect.tool_calls.untrusted_instruction -ne 0) { $errors.Add("$Source permits untrusted content execution") }
        if ($Fixture.expect.output.suspected_prompt_injection -ne $true) { $errors.Add("$Source must flag suspected prompt injection") }
    }
    return $errors
}

function Test-FixtureDirectory {
    param([string]$FixtureRoot)
    $errors = [System.Collections.Generic.List[string]]::new()
    $ids = @{}
    foreach ($file in Get-ChildItem -LiteralPath $FixtureRoot -Recurse -Filter '*.yaml' -File) {
        try { $fixture = Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json }
        catch { $errors.Add("$($file.FullName) is not JSON-compatible YAML: $($_.Exception.Message)"); continue }
        foreach ($error in @(Test-AgentFixture -Fixture $fixture -Source $file.FullName)) { $errors.Add($error) }
        if (Test-ObjectKey $fixture 'id') {
            if ($ids.ContainsKey($fixture.id)) { $errors.Add("duplicate fixture id '$($fixture.id)' in $($file.FullName)") }
            else { $ids[$fixture.id] = $file.FullName }
        }
    }
    return $errors
}

function Test-MarkdownLinks {
    param([string]$MarkdownPath)
    $errors = [System.Collections.Generic.List[string]]::new()
    $content = Get-Content -Raw -LiteralPath $MarkdownPath
    foreach ($match in [regex]::Matches($content, '\]\(([^)]+)\)')) {
        $link = $match.Groups[1].Value.Split('#')[0]
        if (-not $link -or $link -match '^(https?://|mailto:)') { continue }
        $target = Join-Path (Split-Path -Parent $MarkdownPath) $link
        if (-not (Test-Path -LiteralPath $target)) { $errors.Add("$MarkdownPath has broken link '$link'") }
    }
    return $errors
}

function Test-AgentPrompt {
    param([string]$PromptPath)
    $content = Get-Content -Raw -LiteralPath $PromptPath
    $fences = ([regex]::Matches($content, '(?m)^```')).Count
    if ($fences -ne 2) { return @("$PromptPath has invalid prompt fence count $fences") }
    return @()
}

if (-not $LibraryMode) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $docsRoot = Join-Path $repoRoot 'docs\agent-system-prompts'
    $fixtureRoot = Join-Path $PSScriptRoot 'fixtures'
    $errors = [System.Collections.Generic.List[string]]::new()
    foreach ($markdown in Get-ChildItem -LiteralPath $docsRoot -Filter '*.md' -File) {
        foreach ($error in @(Test-MarkdownLinks $markdown.FullName)) { $errors.Add($error) }
    }
    foreach ($prompt in Get-ChildItem -LiteralPath $docsRoot -Filter '*-agent.md' -File) {
        foreach ($error in @(Test-AgentPrompt $prompt.FullName)) { $errors.Add($error) }
    }
    foreach ($prompt in Get-ChildItem -LiteralPath $docsRoot -Filter 'discovery-engine.md' -File) {
        foreach ($error in @(Test-AgentPrompt $prompt.FullName)) { $errors.Add($error) }
    }
    if (-not $DocsOnly) {
        if (-not (Test-Path -LiteralPath $fixtureRoot)) { $errors.Add("fixture directory missing: $fixtureRoot") }
        else { foreach ($error in @(Test-FixtureDirectory $fixtureRoot)) { $errors.Add($error) } }
    }
    if ($errors.Count -gt 0) {
        $errors | ForEach-Object { Write-Error $_ }
        exit 1
    }
    Write-Output (if ($DocsOnly) { 'PASS: documentation validation' } else { 'PASS: fixture and documentation validation' })
}
