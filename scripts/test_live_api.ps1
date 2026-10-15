# Live API End-to-End Test Suite

$BaseUrl = "http://127.0.0.1:8000"
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Running Live API Tests against $BaseUrl " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

function Assert-Step($name, [scriptblock]$action) {
    Write-Host "`n[TEST] $name..." -ForegroundColor Yellow
    try {
        $result = & $action
        Write-Host "[PASS] $name" -ForegroundColor Green
        return $result
    } catch {
        Write-Host "[FAIL] $name : $_" -ForegroundColor Red
        throw $_
    }
}

# 1. Test Root
Assert-Step "Root Frontend (/)" {
    $resp = Invoke-WebRequest -Uri "$BaseUrl/" -Method Get -UseBasicParsing
    if ($resp.StatusCode -ne 200) { throw "Root status code is not 200" }
}

Assert-Step "API Info Endpoint (/api-info)" {
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api-info" -Method Get
    Write-Host "  Response: Name=$($resp.name), Status=$($resp.status), Env=$($resp.environment)" -ForegroundColor Gray
    if ($resp.status -ne "healthy") { throw "Root status is not healthy" }
}

# 2. Test Health
Assert-Step "Health Check Endpoint (/health)" {
    $resp = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
    Write-Host "  Components: API=$($resp.components.api), Database=$($resp.components.database)" -ForegroundColor Gray
    if ($resp.components.database -ne "healthy") { throw "Database is not healthy" }
}

# 3. Test API v1 Health
Assert-Step "API v1 Health Endpoint (/api/v1/health)" {
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/health" -Method Get
    Write-Host "  Response: Status=$($resp.status), Version=$($resp.version)" -ForegroundColor Gray
}

# 4. Test OpenAPI Specification
Assert-Step "OpenAPI JSON Endpoint (/api/v1/openapi.json)" {
    $spec = Invoke-RestMethod -Uri "$BaseUrl/api/v1/openapi.json" -Method Get
    $endpointCount = ($spec.paths.PSObject.Properties | Measure-Object).Count
    Write-Host "  OpenAPI Title: $($spec.info.title) (Total Endpoints: $endpointCount)" -ForegroundColor Gray
}

# 5. Test Prometheus Metrics
Assert-Step "Prometheus Metrics (/metrics)" {
    $metrics = (Invoke-WebRequest -Uri "$BaseUrl/metrics" -UseBasicParsing).Content
    if (-not ($metrics -like "*python_gc_objects_collected_total*")) {
        throw "Prometheus metrics missing expected counters"
    }
    Write-Host "  Metrics collected successfully (Bytes: $($metrics.Length))" -ForegroundColor Gray
}

# 6. Test User Registration
$UniqueUser = "testagent_$(Get-Random)@example.com"
$Password = "StrongAgentPassword123!"
$UserToken = ""

Assert-Step "User Registration (/api/v1/auth/register)" {
    $body = @{ email = $UniqueUser; password = $Password } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/register" -Method Post -Body $body -ContentType "application/json"
    $script:UserToken = $resp.token.access_token
    Write-Host "  Created User ID: $($resp.id), Email: $($resp.email)" -ForegroundColor Gray
}

# 7. Test User Login
Assert-Step "User Login (/api/v1/auth/login)" {
    $form = @{ username = $UniqueUser; password = $Password; grant_type = "password" }
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/login" -Method Post -Body $form
    Write-Host "  Login successful, Token Type: $($resp.token_type)" -ForegroundColor Gray
}

# 8. Test Session Creation
$SessionId = ""
$SessionToken = ""

Assert-Step "Create Chat Session (/api/v1/auth/session)" {
    $headers = @{ Authorization = "Bearer $UserToken" }
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/session" -Method Post -Headers $headers
    $script:SessionId = $resp.session_id
    $script:SessionToken = $resp.token.access_token
    Write-Host "  Session Created: ID=$SessionId" -ForegroundColor Gray
}

# 9. Test List Sessions
Assert-Step "List User Sessions (/api/v1/auth/sessions)" {
    $headers = @{ Authorization = "Bearer $UserToken" }
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/sessions" -Method Get -Headers $headers
    Write-Host "  Found $(($resp | Measure-Object).Count) active session(s)" -ForegroundColor Gray
}

# 10. Test Update Session Name
Assert-Step "Rename Session (/api/v1/auth/session/{id}/name)" {
    $headers = @{ Authorization = "Bearer $SessionToken" }
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/session/$SessionId/name" -Method Patch -Body "name=Live+Test+Conversation" -ContentType "application/x-www-form-urlencoded" -Headers $headers
    Write-Host "  Updated Session Name: $($resp.name)" -ForegroundColor Gray
    if ($resp.name -ne "Live Test Conversation") { throw "Failed to rename session" }
}


# 11. Test Chat History Messages Endpoint
Assert-Step "Fetch Chat Messages (/api/v1/chatbot/messages)" {
    $headers = @{ Authorization = "Bearer $SessionToken" }
    $resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/chatbot/messages" -Method Get -Headers $headers
    Write-Host "  Messages in new session: $(($resp.messages | Measure-Object).Count)" -ForegroundColor Gray
}

# 12. Test Session Deletion
Assert-Step "Delete Session (/api/v1/auth/session/{id})" {
    $headers = @{ Authorization = "Bearer $SessionToken" }
    Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/session/$SessionId" -Method Delete -Headers $headers | Out-Null
    Write-Host "  Session deleted successfully." -ForegroundColor Gray
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " ALL 12 LIVE END-TO-END TESTS PASSED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
