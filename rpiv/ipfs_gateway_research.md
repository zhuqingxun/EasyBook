---
title: IPFS 公共网关和健康检查机制研究笔记
created: 2026-02-06
updated: 2026-02-06
status: completed
tags: [ipfs, gateway, health-check, research]
---

# IPFS 公共网关和健康检查机制研究笔记

## 1. 主流公共 IPFS 网关列表（2025-2026）

根据 [IPFS 官方 Public Gateway Checker](https://github.com/ipfs/public-gateway-checker) 项目，以下是目前仍在运营的公共 IPFS 网关：

### 1.1 官方基础设施网关

| 网关 | URL 模板 | 说明 |
|------|---------|------|
| IPFS.io | `https://ipfs.io/ipfs/<CID>` | IPFS 基金会官方网关，路径解析方式 |
| Dweb.link | `https://dweb.link/ipfs/<CID>` | IPFS 基金会官方网关，子域名解析方式 |
| Trustless Gateway | `https://trustless-gateway.link/ipfs/<CID>` | 仅限可信和可验证的响应 |

### 1.2 商业和社区网关（20个）

根据官方配置文件，截至 2026 年初，以下网关仍在服役：

```
1.  https://ipfs.filebase.io/ipfs/<CID>
2.  https://ipfs.orbitor.dev/ipfs/<CID>
3.  https://latam.orbitor.dev/ipfs/<CID>
4.  https://apac.orbitor.dev/ipfs/<CID>
5.  https://eu.orbitor.dev/ipfs/<CID>
6.  https://dget.top/ipfs/<CID>
7.  https://flk-ipfs.xyz/ipfs/<CID>
8.  https://ipfs.cyou/ipfs/<CID>
9.  https://dlunar.net/ipfs/<CID>
10. https://storry.tv/ipfs/<CID>
11. https://ipfs.io/ipfs/<CID>
12. https://dweb.link/ipfs/<CID>
13. https://gateway.pinata.cloud/ipfs/<CID>
14. https://hardbin.com/ipfs/<CID>
15. https://ipfs.runfission.com/ipfs/<CID>
16. https://ipfs.eth.aragon.network/ipfs/<CID>
17. https://4everland.io/ipfs/<CID>
18. https://w3s.link/ipfs/<CID>
19. https://trustless-gateway.link/ipfs/<CID>
20. https://ipfs.ecolatam.com/ipfs/<CID>
```

### 1.3 已停止服务的网关

**Cloudflare IPFS Gateway 已退役**

- ❌ `cloudflare-ipfs.com` - 2024年8月14日后停止服务
- ❌ `cf-ipfs.com` - 已重定向至 ipfs.io
- 原因：Cloudflare 将流量迁移至 Interplanetary Shipyard 的 IPFS 网关

来源：[Cloudflare's public IPFS gateways blog](https://blog.cloudflare.com/cloudflares-public-ipfs-gateways-and-supporting-interplanetary-shipyard/)

---

## 2. 网关可用性现状

### 2.1 稳定性排名（基于社区反馈）

根据 [IPFS Gateway Best Practices](https://docs.ipfs.tech/how-to/gateway-best-practices/) 文档，推荐的稳定网关：

**一线网关（推荐用于生产环境）：**
- `ipfs.io` - IPFS 基金会维护
- `dweb.link` - IPFS 基金会维护
- `gateway.pinata.cloud` - Pinata 商业网关，无速率限制（针对专用网关）

**二线网关（备选方案）：**
- `ipfs.filebase.io` - Filebase 公共网关，限制 100 RPM
- `w3s.link` - Web3.Storage 网关
- `4everland.io` - 4everland 提供商

### 2.2 实时健康检查

可通过官方工具查看实时状态：
- [IPFS Public Gateway Checker](https://ipfs.github.io/public-gateway-checker/)

---

## 3. CID 格式详解

### 3.1 CIDv0 vs CIDv1 的区别

| 特性 | CIDv0 | CIDv1 |
|------|-------|-------|
| **格式** | 46 字符，以 `Qm` 开头 | 自描述格式，包含版本、编码、哈希信息 |
| **编码方式** | Base58btc（隐式） | 支持多种 Multibase 编码（显式） |
| **默认编码** | Base58btc | Base32（不区分大小写） |
| **Codec** | dag-pb（隐式） | 支持多种 codec（dag-pb、raw、dag-cbor 等） |
| **哈希算法** | SHA-256（隐式） | 显式指定哈希算法 |
| **灵活性** | 低，参数固定 | 高，支持未来扩展 |
| **转换** | 可转换为 CIDv1 | 仅 dag-pb codec 可转 CIDv0 |

**示例：**

```
CIDv0: QmRgutAxd8t7oGkSm4wmeuByG6M51wcTso6cubDdQtuEfL
CIDv1: bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

### 3.2 Anna's Archive 中的 CID 格式

根据 [Anna's Archive IPFS Blog](https://annas-archive.li/blog/putting-5,998,794-books-on-ipfs.html) 说明：

- **哈希算法**：`blake2b-256`
- **分块策略**：`size-1048576` (1 MB)
- **CID 版本**：同时存在 CIDv0 (`Qm...`) 和 CIDv1 (`bafk2bzace...`)

**关键注意事项：**
> 使用相同的哈希算法和分块参数至关重要，否则会生成不同的 CID。

---

## 4. MD5 转 CID 机制

### 4.1 MD5 与 CID 的关系

**核心原理：**
- MD5 是基于文件内容计算的哈希值
- CID 是基于 IPFS DAG 结构计算的内容标识符
- 两者算法不同，**无法直接转换**

### 4.2 LibGen 的存储架构

根据 [LibGen IPFS 架构](https://freeread.org/ipfs/)：

**目录结构：**
```
每个目录包含 1000 本书
目录编号 = floor(book_id / 1000) * 1000

示例：
book_id: 2217239
目录编号: 2217000
访问路径: ipfs get <directory_CID>/<MD5_hash>
```

**实际数据映射：**

| LibGen 数据库字段 | 说明 |
|------------------|------|
| `id` | 书籍唯一 ID |
| `md5` | 文件内容 MD5 哈希 |
| `ipfs_cid` | 对应的 IPFS CID（如果已上传） |

**查询流程：**
1. 通过 MD5 在 LibGen 数据库查询 `id`
2. 计算目录编号：`directory = (id // 1000) * 1000`
3. 查询该目录的 `ipfs_cid`
4. 构造下载路径：`<gateway>/ipfs/<directory_cid>/<md5>`

### 4.3 实用工具

**zlib-searcher**
- GitHub: [Aeres-u99/idk-zlib](https://github.com/Aeres-u99/idk-zlib)
- 功能：搜索 zlib/libgen 索引，获取 IPFS CID
- 导出字段：id, title, author, publisher, extension, filesize, language, year, pages, isbn, ipfs_cid

---

## 5. HEAD 请求检测最佳实践

### 5.1 超时设置

根据 [IPFS Gateway Best Practices](https://docs.ipfs.tech/how-to/gateway-best-practices/)：

**推荐配置：**
```python
# 网关健康检查
CONNECT_TIMEOUT = 5  # 连接超时 5 秒
READ_TIMEOUT = 10    # 读取超时 10 秒

# 实际文件下载
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60    # 根据文件大小调整
```

**关键考虑因素：**
- IPFS 网关可能需要从网络中获取内容（冷启动）
- 504 Gateway Timeout 表示可重试，非永久失败
- 响应头应包含 `Retry-After` 字段

### 5.2 重试策略

**推荐实现：**

```python
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
)
async def check_gateway_health(gateway_url: str, test_cid: str) -> bool:
    """
    检查 IPFS 网关健康状态

    Args:
        gateway_url: 网关基础 URL（如 https://ipfs.io）
        test_cid: 测试用的 CID

    Returns:
        True 表示网关可用，False 表示不可用
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=10.0)) as client:
        url = f"{gateway_url}/ipfs/{test_cid}"
        try:
            response = await client.head(url, follow_redirects=True)
            return response.status_code in {200, 301, 302, 307, 308}
        except (httpx.TimeoutException, httpx.ConnectError):
            return False
```

### 5.3 状态码判断

**可接受的状态码：**

| 状态码 | 含义 | 处理方式 |
|--------|------|----------|
| 200 | 文件存在且可访问 | ✅ 健康 |
| 301/302/307/308 | 重定向 | ✅ 健康（需跟随重定向） |
| 404 | 文件未找到 | ⚠️ 网关正常，但 CID 不存在 |
| 429 | 速率限制 | ⚠️ 需降低请求频率 |
| 502/503/504 | 网关超时 | ❌ 可重试 |
| 连接超时 | 网络不可达 | ❌ 网关不可用 |

**注意事项：**
- 404 不代表网关故障，只表示内容不存在
- 使用 `follow_redirects=True` 处理 CDN 重定向
- 监控 `Retry-After` 响应头

---

## 6. Python 实现：httpx 异步健康检查

### 6.1 完整示例代码

```python
"""
IPFS 网关健康检查器
使用 httpx 异步检测多个网关的可用性
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Dict
import httpx

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class GatewayStatus:
    """网关状态数据类"""
    url: str
    available: bool
    response_time_ms: float
    status_code: int = None
    error_message: str = None


class IPFSGatewayHealthChecker:
    """IPFS 网关健康检查器"""

    # 测试用的小文件 CID（IPFS 白皮书）
    TEST_CID = "QmR7GSQM93Cx5eAg6a6yRzNde1FQv7uL6X1o4k7zrJa3LX"

    # 网关列表
    GATEWAYS = [
        "https://ipfs.io",
        "https://dweb.link",
        "https://gateway.pinata.cloud",
        "https://ipfs.filebase.io",
        "https://w3s.link",
        "https://4everland.io",
        "https://ipfs.cyou",
    ]

    def __init__(
        self,
        gateways: List[str] = None,
        test_cid: str = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
        max_retries: int = 2,
    ):
        """
        初始化健康检查器

        Args:
            gateways: 网关 URL 列表
            test_cid: 测试用的 CID
            connect_timeout: 连接超时（秒）
            read_timeout: 读取超时（秒）
            max_retries: 最大重试次数
        """
        self.gateways = gateways or self.GATEWAYS
        self.test_cid = test_cid or self.TEST_CID
        self.timeout = httpx.Timeout(connect_timeout, read=read_timeout)
        self.max_retries = max_retries

    async def check_single_gateway(
        self,
        gateway_url: str,
        session: httpx.AsyncClient,
    ) -> GatewayStatus:
        """
        检查单个网关的健康状态

        Args:
            gateway_url: 网关基础 URL
            session: httpx 异步客户端

        Returns:
            GatewayStatus 对象
        """
        url = f"{gateway_url}/ipfs/{self.test_cid}"

        for attempt in range(self.max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()
                response = await session.head(url, follow_redirects=True)
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000

                # 检查状态码
                is_available = response.status_code in {200, 301, 302, 307, 308}

                return GatewayStatus(
                    url=gateway_url,
                    available=is_available,
                    response_time_ms=response_time,
                    status_code=response.status_code,
                )

            except httpx.TimeoutException as e:
                if attempt == self.max_retries:
                    logger.warning(f"网关 {gateway_url} 超时（重试 {attempt} 次后）")
                    return GatewayStatus(
                        url=gateway_url,
                        available=False,
                        response_time_ms=-1,
                        error_message=f"Timeout: {str(e)}",
                    )
                # 指数退避
                await asyncio.sleep(2 ** attempt)

            except (httpx.ConnectError, httpx.RequestError) as e:
                logger.warning(f"网关 {gateway_url} 连接失败: {str(e)}")
                return GatewayStatus(
                    url=gateway_url,
                    available=False,
                    response_time_ms=-1,
                    error_message=f"Connection Error: {str(e)}",
                )

    async def check_all_gateways(self) -> List[GatewayStatus]:
        """
        并发检查所有网关

        Returns:
            GatewayStatus 对象列表
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [
                self.check_single_gateway(gateway, client)
                for gateway in self.gateways
            ]
            results = await asyncio.gather(*tasks)

        return results

    def get_healthy_gateways(self, results: List[GatewayStatus]) -> List[str]:
        """
        过滤出健康的网关

        Args:
            results: 检查结果列表

        Returns:
            健康网关的 URL 列表（按响应时间排序）
        """
        healthy = [r for r in results if r.available]
        healthy.sort(key=lambda x: x.response_time_ms)
        return [r.url for r in healthy]

    def print_report(self, results: List[GatewayStatus]):
        """打印健康检查报告"""
        print("\n" + "=" * 70)
        print("IPFS 网关健康检查报告")
        print("=" * 70)

        for result in sorted(results, key=lambda x: x.response_time_ms if x.available else float('inf')):
            status_icon = "✅" if result.available else "❌"
            status_text = f"{result.status_code}" if result.status_code else "N/A"
            time_text = f"{result.response_time_ms:.0f}ms" if result.available else "超时"

            print(f"{status_icon} {result.url:40s} | {status_text:3s} | {time_text:>8s}")

            if result.error_message:
                print(f"   错误: {result.error_message}")

        healthy_count = sum(1 for r in results if r.available)
        print(f"\n健康网关数量: {healthy_count}/{len(results)}")
        print("=" * 70 + "\n")


# 使用示例
async def main():
    """主函数示例"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建健康检查器
    checker = IPFSGatewayHealthChecker()

    # 执行检查
    print("开始检查 IPFS 网关健康状态...")
    results = await checker.check_all_gateways()

    # 打印报告
    checker.print_report(results)

    # 获取健康的网关列表
    healthy_gateways = checker.get_healthy_gateways(results)
    print("推荐使用的网关（按速度排序）:")
    for i, gateway in enumerate(healthy_gateways[:3], 1):
        print(f"  {i}. {gateway}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 高级功能：限流和熔断

```python
import time
from collections import deque
from typing import Optional

class RateLimitedGateway:
    """带限流功能的网关包装器"""

    def __init__(
        self,
        gateway_url: str,
        rpm_limit: int = 100,  # 每分钟请求数
        circuit_breaker_threshold: int = 5,  # 连续失败次数阈值
        circuit_breaker_timeout: float = 60.0,  # 熔断恢复时间（秒）
    ):
        self.gateway_url = gateway_url
        self.rpm_limit = rpm_limit
        self.request_times = deque(maxlen=rpm_limit)

        # 熔断器状态
        self.failure_count = 0
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_open_until: Optional[float] = None
        self.circuit_breaker_timeout = circuit_breaker_timeout

    def is_rate_limited(self) -> bool:
        """检查是否超过速率限制"""
        now = time.time()
        # 清理 60 秒前的记录
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()

        return len(self.request_times) >= self.rpm_limit

    def is_circuit_open(self) -> bool:
        """检查熔断器是否开启"""
        if self.circuit_open_until is None:
            return False

        if time.time() >= self.circuit_open_until:
            # 熔断器恢复
            self.circuit_open_until = None
            self.failure_count = 0
            return False

        return True

    def record_request(self):
        """记录请求时间"""
        self.request_times.append(time.time())

    def record_success(self):
        """记录成功请求"""
        self.failure_count = 0

    def record_failure(self):
        """记录失败请求"""
        self.failure_count += 1
        if self.failure_count >= self.circuit_breaker_threshold:
            # 开启熔断器
            self.circuit_open_until = time.time() + self.circuit_breaker_timeout
            logger.warning(
                f"网关 {self.gateway_url} 熔断器开启，"
                f"{self.circuit_breaker_timeout}秒后恢复"
            )

    async def wait_if_rate_limited(self):
        """如果超过限流则等待"""
        if self.is_rate_limited():
            oldest_request = self.request_times[0]
            wait_time = 60 - (time.time() - oldest_request)
            if wait_time > 0:
                logger.info(f"网关 {self.gateway_url} 达到限流阈值，等待 {wait_time:.1f} 秒")
                await asyncio.sleep(wait_time)


# 使用示例
class SmartGatewaySelector:
    """智能网关选择器（带限流和熔断）"""

    def __init__(self, gateways: List[str]):
        self.gateways = {
            url: RateLimitedGateway(url, rpm_limit=80)  # 留 20% 余量
            for url in gateways
        }

    async def get_available_gateway(self) -> Optional[str]:
        """获取可用的网关"""
        for gateway_url, limiter in self.gateways.items():
            if limiter.is_circuit_open():
                continue
            if not limiter.is_rate_limited():
                return gateway_url

        # 所有网关都受限，等待最快恢复的
        logger.warning("所有网关都受限或熔断，等待恢复...")
        await asyncio.sleep(5)
        return await self.get_available_gateway()

    async def download_file(self, cid: str, output_path: str) -> bool:
        """
        下载 IPFS 文件（自动选择网关）

        Args:
            cid: IPFS CID
            output_path: 输出文件路径

        Returns:
            是否下载成功
        """
        gateway_url = await self.get_available_gateway()
        limiter = self.gateways[gateway_url]

        # 检查熔断器
        if limiter.is_circuit_open():
            logger.error(f"网关 {gateway_url} 熔断器开启")
            return False

        # 等待限流
        await limiter.wait_if_rate_limited()

        # 记录请求
        limiter.record_request()

        # 执行下载
        url = f"{gateway_url}/ipfs/{cid}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=60.0)) as client:
                response = await client.get(url)
                response.raise_for_status()

                with open(output_path, 'wb') as f:
                    f.write(response.content)

                limiter.record_success()
                logger.info(f"从 {gateway_url} 下载成功: {cid}")
                return True

        except Exception as e:
            limiter.record_failure()
            logger.error(f"从 {gateway_url} 下载失败: {str(e)}")
            return False
```

---

## 7. 网关限流策略

### 7.1 各网关限流政策（2025-2026）

| 网关 | 限流策略 | 备注 |
|------|---------|------|
| **ipfs.io** | 基于 IP 和子网的 DoS 保护 | 滥用会被封禁，不适合网站托管 |
| **dweb.link** | 同 ipfs.io | IPFS 基金会统一管理 |
| **gateway.pinata.cloud** | 专用网关无限制 | 公共网关有限制 |
| **ipfs.filebase.io** | 100 RPM（每分钟请求数） | 严格限制 |
| **其他商业网关** | 依提供商而定 | 需查阅具体文档 |

来源：
- [IPFS Public Utilities Documentation](https://docs.ipfs.tech/concepts/public-utilities/)
- [MetaMask IPFS Rate Limits](https://docs.metamask.io/services/how-to/use-ipfs/request-rate-limits/)

### 7.2 新特性（2025）

根据 [Shipyard 2025 Review](https://ipshipyard.com/blog/2025-shipyard-ipfs-year-in-review/)：

> **go-libp2p v0.42 引入的新功能：**
> - 每 IP 和每子网的 DoS 保护
> - QUIC 源地址验证
> - 速率限制机制

### 7.3 避免被封的最佳实践

**推荐策略：**

1. **尊重限流：** 实现客户端限流，留 20% 余量
   ```python
   # Filebase 限制 100 RPM，设置为 80 RPM
   MAX_RPM = 80
   ```

2. **网关轮询：** 分散请求到多个网关
   ```python
   gateways = ["gateway1", "gateway2", "gateway3"]
   current_gateway = itertools.cycle(gateways)
   ```

3. **缓存机制：** 缓存已下载的内容
   ```python
   # 使用本地 IPFS 节点缓存
   # 或使用 CDN（如 Cloudflare）作为前端
   ```

4. **使用 CDN：** 在网关前部署 CDN
   - 官方建议：将 Cloudflare 放在 IPFS 网关前面

5. **监控 Retry-After：** 遵守服务器的重试指示
   ```python
   retry_after = response.headers.get("Retry-After")
   if retry_after:
       await asyncio.sleep(int(retry_after))
   ```

6. **避免的行为：**
   - ❌ 使用公共网关托管网站
   - ❌ 高频轮询同一 CID
   - ❌ 忽略 429 状态码继续请求
   - ❌ 使用单一网关处理所有流量

---

## 8. 备用下载方案

### 8.1 LibGen 直接 HTTP 链接

根据 [LibGen Guide](https://librarygenesis.net/)，LibGen 提供以下下载方式：

**方式 1：LibGen 镜像站直接下载**
```
https://libgen.li/ads.php?md5=<MD5_HASH>
https://libgen.is/book/index.php?md5=<MD5_HASH>
```

**方式 2：IPFS 网关下载**
```
https://ipfs.io/ipfs/<DIRECTORY_CID>/<MD5_HASH>
```

**方式 3：Torrent**
- LibGen 提供完整数据集的种子文件
- 工具：[libgen-seedtools](https://github.com/subdavis/libgen-seedtools)

### 8.2 Anna's Archive 多源下载

[Anna's Archive](https://annas-archive.li/) 聚合了多个数据源：

**支持的下载源：**
1. **IPFS** - 通过公共网关
2. **LibGen 镜像** - 直接 HTTP 链接
3. **Sci-Hub** - 学术论文
4. **Z-Library** - 备用源

**推荐下载优先级：**
```python
DOWNLOAD_PRIORITY = [
    "libgen_direct",    # 最快，HTTP 直连
    "ipfs_cached",      # 如果网关已缓存
    "zlibrary",         # 备用方案
    "ipfs_uncached",    # 最慢，需从网络获取
]
```

### 8.3 故障转移策略

```python
async def download_with_fallback(
    md5: str,
    ipfs_cid: Optional[str] = None,
    output_path: str = None,
) -> bool:
    """
    多源下载，自动故障转移

    Args:
        md5: 文件 MD5 哈希
        ipfs_cid: IPFS CID（可选）
        output_path: 输出路径

    Returns:
        是否下载成功
    """
    # 尝试 1: LibGen 直接链接
    try:
        libgen_url = f"https://libgen.li/get.php?md5={md5}"
        async with httpx.AsyncClient() as client:
            response = await client.get(libgen_url, follow_redirects=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"从 LibGen 直连下载成功: {md5}")
                return True
    except Exception as e:
        logger.warning(f"LibGen 直连失败: {str(e)}")

    # 尝试 2: IPFS 网关
    if ipfs_cid:
        for gateway in ["https://ipfs.io", "https://dweb.link", "https://gateway.pinata.cloud"]:
            try:
                url = f"{gateway}/ipfs/{ipfs_cid}"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"从 IPFS 网关下载成功: {gateway}")
                        return True
            except Exception as e:
                logger.warning(f"IPFS 网关 {gateway} 失败: {str(e)}")

    # 尝试 3: Anna's Archive API（如果可用）
    try:
        aa_url = f"https://annas-archive.se/md5/{md5}"
        # 解析页面获取下载链接
        # （需要实现 HTML 解析逻辑）
        logger.info("尝试从 Anna's Archive 下载...")
        # ... 省略实现细节
    except Exception as e:
        logger.warning(f"Anna's Archive 失败: {str(e)}")

    logger.error(f"所有下载源均失败: {md5}")
    return False
```

### 8.4 当前 LibGen 状况（2024-2025）

根据 [Wikipedia LibGen Article](https://en.wikipedia.org/wiki/Library_Genesis)：

> **2024 年 12 月状况：**
> - 多数 LibGen 域名被出版商诉讼导致关闭
> - 部分镜像站仍可访问但速度较慢
> - 推荐使用 Anna's Archive 作为统一入口

**建议：**
- ✅ 使用 Anna's Archive 作为主要搜索入口
- ✅ 实现多源下载和自动故障转移
- ✅ 部署本地 IPFS 节点缓存常用内容
- ⚠️ 关注 LibGen 镜像站的可用性变化

---

## 9. 实战工具集成

### 9.1 推荐的 Python 库

```toml
# pyproject.toml
[project]
dependencies = [
    "httpx>=0.27.0",           # 异步 HTTP 客户端
    "tenacity>=8.2.0",         # 重试机制
    "aiofiles>=23.0.0",        # 异步文件 I/O
    "cachetools>=5.3.0",       # 缓存工具
]
```

### 9.2 完整的生产级下载器

见 `/src/ipfs_downloader.py`（完整代码太长，这里仅列出架构）

**核心模块：**
```
ipfs_downloader/
├── gateway_manager.py      # 网关管理和健康检查
├── rate_limiter.py         # 限流和熔断器
├── downloader.py           # 下载逻辑
├── cache.py                # 缓存管理
└── utils.py                # 工具函数
```

---

## 10. 参考资源

### 10.1 官方文档

- [IPFS Documentation](https://docs.ipfs.tech/)
- [IPFS Gateway Specification](https://specs.ipfs.tech/http-gateways/)
- [Public Gateway Checker](https://ipfs.github.io/public-gateway-checker/)
- [IPFS Best Practices](https://docs.ipfs.tech/how-to/gateway-best-practices/)

### 10.2 相关项目

- [ipfs/public-gateway-checker](https://github.com/ipfs/public-gateway-checker) - 官方网关检查器
- [ipfs-shipyard/py-ipfs-http-client](https://github.com/ipfs-shipyard/py-ipfs-http-client) - Python IPFS 客户端
- [fsspec/ipfsspec](https://github.com/fsspec/ipfsspec) - Python IPFS fsspec 实现
- [subdavis/libgen-seedtools](https://github.com/subdavis/libgen-seedtools) - LibGen 种子管理工具

### 10.3 博客和讨论

- [Anna's Archive IPFS Blog](https://annas-archive.li/blog/putting-5,998,794-books-on-ipfs.html)
- [Cloudflare IPFS Gateway Sunset](https://blog.cloudflare.com/cloudflares-public-ipfs-gateways-and-supporting-interplanetary-shipyard/)
- [The Saga of IPFS - Libgen and Cloudflare](https://jackiejude.me/posts/ipfs-libgen-cloudflare/)

---

## 总结

### 关键要点

1. **网关选择：** 优先使用 IPFS 基金会官方网关（ipfs.io、dweb.link），商业网关作为备选
2. **Cloudflare 已退役：** 不要再使用 cloudflare-ipfs.com
3. **CID 格式：** 理解 CIDv0/CIDv1 的区别，注意分块参数
4. **MD5 不能直接转 CID：** 需要通过数据库映射
5. **健康检查：** 使用 HEAD 请求，设置合理的超时和重试
6. **限流至关重要：** 实现客户端限流和熔断机制
7. **多源下载：** 不要依赖单一来源，实现故障转移

### 生产环境检查清单

- [ ] 实现网关健康检查和自动切换
- [ ] 配置合理的超时（连接 5s，读取 10-60s）
- [ ] 实现指数退避重试策略
- [ ] 监控和遵守限流政策（留 20% 余量）
- [ ] 实现熔断器防止雪崩
- [ ] 部署 CDN 或缓存层
- [ ] 实现多源下载和故障转移
- [ ] 监控网关可用性和响应时间
- [ ] 定期更新网关列表
- [ ] 记录详细的错误日志

---

**最后更新：** 2026-02-06
**数据来源：** IPFS 官方文档、GitHub 开源项目、社区讨论
