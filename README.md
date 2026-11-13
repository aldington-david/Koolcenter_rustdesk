# RustDesk 远程控制

## 安装此 fork 的更新包

插件版本 **1.4.9**，内置 RustDesk Server **1.1.16**。从本仓库的 [Releases](https://github.com/aldington-david/Koolcenter_rustdesk/releases) 下载 `rustdesk.tar.gz`，在路由器「软件中心 → 离线安装」上传并覆盖安装，然后开启插件。

升级前先在插件页面停止服务，并备份 `/koolshare/configs/rustdesk/`。覆盖安装会保留这个目录中的数据库和密钥；完整的磁盘密钥对优先于软件中心缓存，并同步更新页面上的公钥。**请直接覆盖升级；卸载操作会删除原有数据。**

### GT-AC5300 / 386_51529_koolcenter / USB2JFFS 2.2.0

对于 `/tmp/mnt/sda1/.koolshare_jffs → /jffs` 的 ext4 绑定挂载，本版本直接读取 `/proc/mounts` 中 `/jffs` 的文件系统类型，启动前检查数据目录读写。`df` 隐藏绑定挂载或同一设备存在多个挂载点时，都可正确识别。

`hbbs` 和 `hbbr` 的工作目录、密钥和数据库继续使用 `/koolshare/configs/rustdesk/`；服务的 `HOME` 固定到这个目录，`XDG_CONFIG_HOME` 固定到其中的 `.config/`，解决继承的配置路径不可写所触发的 `Failed to store config: Failed to create directory`。

rc.3 的启动读写检查使用基础 Shell 操作，支持未提供 `mktemp` 的精简固件。目录创建、权限设置、文件写入和读取失败会分别记录，并保留系统错误，方便定位具体原因。

启动日志应显示「RustDesk 数据目录读写正常（文件系统：ext4）」，页面上的两个程序版本均为 `1.1.16`，随后显示 `hbbs` 和 `hbbr` 正常运行。Linux 4.1 原生 JFFS2 的兼容性拦截继续保留；遇到此提示时，应检查 USB2JFFS 是否确实把 ext4 分区挂载到了 `/jffs`。

### 构建与验证

在仓库目录运行 `python3 build.py` 即可生成 `rustdesk.tar.gz`，并更新软件中心使用的 `config.json.js` 校验值。构建脚本使用 Python 3 标准库，支持 Windows 和 Linux。

Linux 下安装 BusyBox 和 `qemu-user` 后，运行 `python3 -m unittest discover -s tests -v`。测试覆盖绑定挂载误判、不可写目录、升级保留密钥和数据库、离线包权限，以及通过实际启动脚本运行 ARM 版 `hbbs` / `hbbr`。ARM 测试检查五个 TCP 监听端口、配置文件写入和 SQLite 完整性；GT-AC5300 实机安装与远程连接仍需实机验证。

本包沿用原插件的 ARMv7 部署方式。三个服务端程序均直接来自 [RustDesk Server 1.1.16 官方 ARMv7 发布包](https://github.com/rustdesk/rustdesk-server/releases/tag/1.1.16)，采用静态 musl 构建，未修改服务端源码、未使用 UPX 压缩。对应源码见 [官方 1.1.16 标签](https://github.com/rustdesk/rustdesk-server/tree/1.1.16)，AGPL-3.0 许可随包保存在 `rustdesk/res/rustdesk-server-LICENSE`。插件脚本原始仓库为 [everstu/Koolcenter_rustdesk](https://github.com/everstu/Koolcenter_rustdesk)，保留其 MIT 许可。

## 是什么？
`RustDesk是一款优秀的免费开源的远程控制软件，适合所有人的虚拟/远程桌面基础设施！ 开源 TeamViewer / Citrix 替代品。`


## 项目地址
RustDesk:
https://github.com/rustdesk/rustdesk

RustDesk Server:
https://github.com/rustdesk/rustdesk-server


## 官方信息  

官网地址：https://rustdesk.com/

官方Github：https://github.com/rustdesk/rustdesk

官网文档 https://rustdesk.com/docs/zh-cn/

---

## 机型支持

在asuswrt为基础的固件上，Rustdesk Server插件目前仅支持如下架构的路由器：

- 部分及其未列出，请根据CPU型号和支持软件中心与否自行判断
- 使用Rustdesk Server建议配置1G及以上的虚拟内存，特别是小内存的路由器

| 机型             | 内存  | CPU/SOC | 架构  | 核心 | 频率    | 插件支持 |
| ---------------- | ----- | ------- | ----- | ---- | ------- | ------------- |
| RT-AC86U         | 512MB | BCM4906 | armv8 | 2    | 1.8 GHz | ✔️             |
| GT-AC2900        | 512MB | BCM4906 | armv8 | 2    | 1.8 GHz | ✔️             |
| RT-AX92U         | 512MB | BCM4906 | armv8 | 2    | 1.8 GHz | ✔️             |
| GT-AC5300        | 1GB   | BCM4908 | armv8 | 4    | 1.8 GHz | ✔️             |
| RT-AX88U         | 1GB   | BCM4908 | armv8 | 4    | 1.8 GHz | ✔️             |
| GT-AX11000       | 1GB   | BCM4908 | armv8 | 4    | 1.8 GHz | ✔️             |
| NetGear RAX80    | 1GB   | BCM4908 | armv8 | 4    | 1.8 GHz | ✔️             |
| RT-AX68U         | 512MB | BCM4906 | armv8 | 2    | 1.8 GHz | ✔️             |
| RT-AX86U         | 1GB   | BCM4908 | armv8 | 4    | 1.8 GHz | ✔️             |
| GT-AXE11000      | 1GB   | BCM4908 | armv8 | 4    | 1.8 GHz | ✔️             |
| ZenWiFi_Pro_XT12 | 1GB   | BCM4912 | armv8 | 4    | 2.0GHz  | ✔️             |
| GT-AX6000        | 1GB   | BCM4912 | armv8 | 4    | 2.0GHz  | ✔️             |
| GT-AX11000_PRO   | 1GB   | BCM4912 | armv8 | 4    | 2.0GHz  | ✔️             |
| RT-AX86U_PRO     | 1GB   | BCM4912 | armv8 | 4    | 2.0GHz  | ✔️             |
| RAX50            | 512MB | BCM6750 | armv7 | 3    | 1.5 GHz | ✔️            |
| RAX70            | 512MB | BCM6755 | armv7 | 4    | 1.5 GHz | ✔️              |
| RT-AX56U         | 512MB | BCM6755 | armv7 | 4    | 1.5 GHz | ✔️            |
| RT-AX56U_V2      | 256MB | BCM6755 | armv7 | 4    | 1.5 GHz | ✔️            |
| RT-AX58U         | 512MB | BCM6750 | armv7 | 3    | 1.5 GHz | ✔️             |
| RT-AX82U         | 512MB | BCM6750 | armv7 | 3    | 1.5 GHz | ✔️              |
| TUF-AX3000       | 512MB | BCM6750 | armv7 | 3    | 1.5 GHz | ✔️              |
| TUF-AX5400       | 512MB | BCM6750 | armv7 | 3    | 1.5 GHz | ✔️              |
| ZenWiFi_XT8      | 512MB | BCM6755 | armv7 | 4    | 1.5 GHz | ✔️              |
| ZenWiFi_XD4      | 256MB | BCM6755 | armv7 | 4    | 1.5 GHz | ✔️              |
| TUF-AX3000_V2    | 512MB | BCM6756 | armv7 | 4    | 1.7GHz  | ✔️             |
| RT-AX57          | 256MB | BCM6756 | armv7 | 4    | 1.7GHz  | ✔️              |
