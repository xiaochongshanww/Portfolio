#!/bin/bash
# 部署验证和测试脚本

set -euo pipefail

# 配置变量
BASE_URL=${BASE_URL:-"http://localhost"}
API_URL="${BASE_URL}/api/v1"
TIMEOUT=${TIMEOUT:-30}
VERBOSE=${VERBOSE:-false}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# HTTP请求函数
http_get() {
    local url="$1"
    local expected_status="${2:-200}"
    
    if [ "${VERBOSE}" = "true" ]; then
        log_info "GET ${url}"
    fi
    
    local response
    response=$(curl -s -w "\n%{http_code}" --connect-timeout "${TIMEOUT}" "${url}" 2>/dev/null || echo -e "\n000")
    local body=$(echo "${response}" | head -n -1)
    local status=$(echo "${response}" | tail -n 1)
    
    if [ "${status}" = "${expected_status}" ]; then
        if [ "${VERBOSE}" = "true" ]; then
            log_success "HTTP ${status} - ${url}"
        fi
        echo "${body}"
        return 0
    else
        log_error "HTTP ${status} (expected ${expected_status}) - ${url}"
        return 1
    fi
}

# JSON响应验证
validate_json_response() {
    local response="$1"
    local expected_keys="$2"
    
    if ! echo "${response}" | jq . >/dev/null 2>&1; then
        log_error "响应不是有效的JSON格式"
        return 1
    fi
    
    for key in ${expected_keys}; do
        if ! echo "${response}" | jq -e ".${key}" >/dev/null 2>&1; then
            log_error "响应中缺少必需的键: ${key}"
            return 1
        fi
    done
    
    return 0
}

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
    local test_name="$1"
    local test_func="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_info "运行测试: ${test_name}"
    
    if ${test_func}; then
        log_success "✓ ${test_name}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "✗ ${test_name}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# =====================================
# 基础连接测试
# =====================================

test_basic_connectivity() {
    log_info "测试基础连接性..."
    http_get "${BASE_URL}" 200 >/dev/null
}

test_health_endpoint() {
    log_info "测试健康检查端点..."
    local response
    response=$(http_get "${API_URL}/health" 200)
    validate_json_response "${response}" "status"
}

test_nginx_status() {
    log_info "测试Nginx状态页面..."
    http_get "${BASE_URL}/nginx_status" 200 >/dev/null 2>&1 || return 0  # 可选测试
}

# =====================================
# API端点测试
# =====================================

test_openapi_spec() {
    log_info "测试OpenAPI规范..."
    local response
    response=$(http_get "${API_URL}/openapi.json" 200)
    validate_json_response "${response}" "openapi info paths"
}

test_public_endpoints() {
    log_info "测试公共API端点..."
    
    # 测试文章列表
    local articles_response
    articles_response=$(http_get "${BASE_URL}/public/articles?page=1&size=5" 200)
    validate_json_response "${articles_response}" "data meta"
    
    # 测试分类列表
    local categories_response
    categories_response=$(http_get "${BASE_URL}/public/categories" 200)
    validate_json_response "${categories_response}" "data"
}

test_cors_headers() {
    log_info "测试CORS头配置..."
    local response
    response=$(curl -s -I -X OPTIONS "${API_URL}/health" -H "Origin: http://example.com" 2>/dev/null || echo "")
    
    if echo "${response}" | grep -qi "access-control-allow-origin"; then
        return 0
    else
        log_warning "CORS头可能未正确配置"
        return 1
    fi
}

# =====================================
# 安全测试
# =====================================

test_security_headers() {
    log_info "测试安全头配置..."
    local response
    response=$(curl -s -I "${BASE_URL}" 2>/dev/null || echo "")
    
    local security_headers=("X-Frame-Options" "X-Content-Type-Options" "X-XSS-Protection")
    local missing_headers=()
    
    for header in "${security_headers[@]}"; do
        if ! echo "${response}" | grep -qi "${header}"; then
            missing_headers+=("${header}")
        fi
    done
    
    if [ ${#missing_headers[@]} -eq 0 ]; then
        return 0
    else
        log_warning "缺少安全头: ${missing_headers[*]}"
        return 1
    fi
}

test_server_info_disclosure() {
    log_info "测试服务器信息泄露..."
    local response
    response=$(curl -s -I "${BASE_URL}" 2>/dev/null || echo "")
    
    if echo "${response}" | grep -qi "server: nginx"; then
        log_warning "服务器版本信息可能泄露"
        return 1
    fi
    
    return 0
}

# =====================================
# 性能测试
# =====================================

test_response_time() {
    log_info "测试响应时间..."
    local start_time
    local end_time
    local duration
    
    start_time=$(date +%s%N)
    http_get "${API_URL}/health" 200 >/dev/null
    end_time=$(date +%s%N)
    
    duration=$(( (end_time - start_time) / 1000000 )) # 毫秒
    
    if [ "${duration}" -lt 1000 ]; then
        log_success "响应时间: ${duration}ms"
        return 0
    else
        log_warning "响应时间较慢: ${duration}ms"
        return 1
    fi
}

test_static_file_caching() {
    log_info "测试静态文件缓存..."
    local response
    response=$(curl -s -I "${BASE_URL}/favicon.ico" 2>/dev/null || curl -s -I "${BASE_URL}/static/logo.svg" 2>/dev/null || echo "")
    
    if echo "${response}" | grep -qi "cache-control"; then
        return 0
    else
        log_warning "静态文件缓存头可能未设置"
        return 1
    fi
}

# =====================================
# 数据库连接测试
# =====================================

test_database_connectivity() {
    log_info "测试数据库连接..."
    # 通过健康检查API间接测试数据库连接
    local response
    response=$(http_get "${API_URL}/health" 200)
    
    if echo "${response}" | jq -e '.database' >/dev/null 2>&1; then
        local db_status
        db_status=$(echo "${response}" | jq -r '.database')
        if [ "${db_status}" = "ok" ] || [ "${db_status}" = "healthy" ]; then
            return 0
        fi
    fi
    
    log_error "数据库连接状态异常"
    return 1
}

# =====================================
# 文件上传测试
# =====================================

test_upload_directory() {
    log_info "测试上传目录访问..."
    # 尝试访问上传目录（应该返回403或404，不应该是500）
    local status
    status=$(curl -s -w "%{http_code}" -o /dev/null "${BASE_URL}/uploads/" 2>/dev/null || echo "000")
    
    if [ "${status}" = "403" ] || [ "${status}" = "404" ] || [ "${status}" = "200" ]; then
        return 0
    else
        log_error "上传目录配置可能有问题，状态码: ${status}"
        return 1
    fi
}

# =====================================
# 容器健康测试
# =====================================

test_container_status() {
    log_info "测试容器状态..."
    
    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker命令不可用，跳过容器测试"
        return 0
    fi
    
    local containers=("blog_backend" "blog_frontend" "blog_gateway")
    local failed_containers=()
    
    for container in "${containers[@]}"; do
        if ! docker ps --format "table {{.Names}}" | grep -q "${container}"; then
            failed_containers+=("${container}")
        fi
    done
    
    if [ ${#failed_containers[@]} -eq 0 ]; then
        return 0
    else
        log_error "以下容器未运行: ${failed_containers[*]}"
        return 1
    fi
}

# =====================================
# 主测试函数
# =====================================

run_all_tests() {
    log_info "开始部署验证测试..."
    echo "目标URL: ${BASE_URL}"
    echo "超时设置: ${TIMEOUT}秒"
    echo "================================"
    
    # 基础测试
    run_test "基础连接性" test_basic_connectivity
    run_test "健康检查端点" test_health_endpoint
    run_test "Nginx状态页面" test_nginx_status
    
    # API测试
    run_test "OpenAPI规范" test_openapi_spec
    run_test "公共API端点" test_public_endpoints
    run_test "CORS头配置" test_cors_headers
    
    # 安全测试
    run_test "安全头配置" test_security_headers
    run_test "服务器信息泄露" test_server_info_disclosure
    
    # 性能测试
    run_test "响应时间" test_response_time
    run_test "静态文件缓存" test_static_file_caching
    
    # 基础设施测试
    run_test "数据库连接" test_database_connectivity
    run_test "上传目录" test_upload_directory
    run_test "容器状态" test_container_status
    
    # 测试总结
    echo "================================"
    log_info "测试完成"
    echo "总测试数: ${TOTAL_TESTS}"
    echo -e "${GREEN}通过: ${PASSED_TESTS}${NC}"
    echo -e "${RED}失败: ${FAILED_TESTS}${NC}"
    
    if [ "${FAILED_TESTS}" -eq 0 ]; then
        log_success "所有测试通过！部署验证成功 🎉"
        return 0
    else
        log_error "有 ${FAILED_TESTS} 个测试失败"
        return 1
    fi
}

# =====================================
# 脚本入口
# =====================================

# 检查依赖
for cmd in curl jq; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        log_error "缺少必需的命令: ${cmd}"
        echo "请安装: apt-get install ${cmd} 或 brew install ${cmd}"
        exit 1
    fi
done

# 显示帮助信息
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat << EOF
Flask Blog 部署验证测试脚本

用法:
  $0 [选项]

选项:
  -h, --help     显示帮助信息
  
环境变量:
  BASE_URL       基础URL (默认: http://localhost)
  TIMEOUT        请求超时时间 (默认: 30)
  VERBOSE        详细输出 (默认: false)

示例:
  $0                                    # 默认测试
  BASE_URL=https://yourdomain.com $0    # 测试生产环境
  VERBOSE=true $0                       # 详细输出
EOF
    exit 0
fi

# 运行测试
run_all_tests