$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'validate-fixtures.ps1') -LibraryMode

$failures = [System.Collections.Generic.List[string]]::new()

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { $script:failures.Add($Message) }
}

function New-ValidFixture {
    return [ordered]@{
        fixture_version = '1.0'
        id = 'broker-duplicate-booking'
        name = 'Duplicate booking returns stored result'
        agent = 'broker'
        given = @{ ledger = @{ state = 'SUCCEEDED' } }
        expect = @{
            output = @{ status = 'EXECUTED'; replayed = $true }
            tool_calls = @{ booking_provider = 0 }
        }
        invariants = @('broker_replay_has_no_provider_call')
    }
}

$validErrors = @(Test-AgentFixture -Fixture (New-ValidFixture) -Source 'fixture.yaml')
Assert-True ($validErrors.Count -eq 0) 'valid fixture should pass'

$missing = New-ValidFixture
$missing.Remove('expect')
$missingErrors = @(Test-AgentFixture -Fixture $missing -Source 'fixture.yaml')
Assert-True (($missingErrors -join ' ') -match 'expect') 'missing expect should fail'

$replay = New-ValidFixture
$replay.expect.tool_calls.booking_provider = 1
$replayErrors = @(Test-AgentFixture -Fixture $replay -Source 'fixture.yaml')
Assert-True (($replayErrors -join ' ') -match 'provider call') 'replay provider call should fail'

$mismatch = New-ValidFixture
$mismatch.id = 'broker-approval-mismatch'
$mismatch.expect.output.status = 'EXECUTED'
$mismatch.expect.tool_calls.booking_provider = 1
$mismatch.invariants = @('approval_mismatch_stops_execution')
$mismatchErrors = @(Test-AgentFixture -Fixture $mismatch -Source 'fixture.yaml')
Assert-True (($mismatchErrors -join ' ') -match 'stop status') 'approval mismatch without stop should fail'

$unsupportedStatus = New-ValidFixture
$unsupportedStatus.id = 'broker-unsupported-authorization-status'
$unsupportedStatus.expect.output.status = 'AUTHORIZATION_REQUIRED'
$unsupportedStatus.expect.tool_calls.booking_provider = 0
$unsupportedStatus.invariants = @('approval_mismatch_stops_execution')
$unsupportedStatusErrors = @(Test-AgentFixture -Fixture $unsupportedStatus -Source 'fixture.yaml')
Assert-True (($unsupportedStatusErrors -join ' ') -match 'stop status') 'unsupported authorization status should fail'

$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ('agent-fixtures-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    $json = New-ValidFixture | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText((Join-Path $temporary 'one.yaml'), $json)
    [System.IO.File]::WriteAllText((Join-Path $temporary 'two.yaml'), $json)
    $duplicateErrors = @(Test-FixtureDirectory -FixtureRoot $temporary)
    Assert-True (($duplicateErrors -join ' ') -match 'duplicate fixture id') 'duplicate IDs should fail'

    $readme = Join-Path $temporary 'README.md'
    [System.IO.File]::WriteAllText($readme, '[missing](not-here.md)')
    $linkErrors = @(Test-MarkdownLinks -MarkdownPath $readme)
    Assert-True (($linkErrors -join ' ') -match 'broken link') 'missing link target should fail'

    $prompt = Join-Path $temporary 'broker-agent.md'
    [System.IO.File]::WriteAllText($prompt, "# Broker`n`n```text`nSYSTEM PROMPT")
    $promptErrors = @(Test-AgentPrompt -PromptPath $prompt)
    Assert-True (($promptErrors -join ' ') -match 'fence') 'unbalanced fence should fail'
}
finally {
    Remove-Item -LiteralPath $temporary -Recurse -Force
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output 'PASS: 8 validator tests'
