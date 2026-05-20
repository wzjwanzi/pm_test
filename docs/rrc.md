# RRC 测试用例

## 1. 基础信息

- 基站 IP：`192.168.13.236`
- Web 端口：`8400`
- Web 账号：`root`
- Web 密码：`5GNR@root`
- SSH 端口：`22`
- SSH 账号：`root`
- SSH 密码：`Root@236_`
- 终端 IP：`10.6.250.2`
- 日志保存目录：`D:\test\mobile_automation_platform\ssh_log`

## 2. 测试目的

验证 RRC 相关操作过程中，能够完整收集以下日志：

- RLC/UP 日志
- 速率日志
- CPU 日志
- Web 本地抓包

## 3. 操作步骤

### 3.1 启动 Web 抓包

1. 登录基站 Web：`http://192.168.13.236:8400`
2. 进入调试信息页面。
3. 选择本地抓包。
4. 勾选信令面。
5. 启动抓包。

预期结果：Web 抓包开始运行。

### 3.2 启动 RLC/UP 日志

SSH 登录基站：

```bash
ssh root@192.168.13.236
```

执行以下命令，并将输出保存到 `D:\test\mobile_automation_platform\ssh_log` 下的 RLC/UP 日志文件：

```bash
while true; do
  odi -n duapp0 dump-rlc-om-info
  odi -n duapp0 display-mac-non-zero-om 1
  odi -n duapp0 display-mac-non-zero-om 2
  odi -n upapp net-stat
  date
  sleep 1
done
```

预期结果：持续收取 RLC/UP 日志。

### 3.3 启动速率日志

执行以下命令，并将输出保存到 `D:\test\mobile_automation_platform\ssh_log` 下的速率日志文件：

```bash
numOfDuapp=`ps -ef | grep mac_phy_intf | grep duapp | wc -l`
while true; do
  clear
  for ((i=0;i<$numOfDuapp;i++)); do
    odi -q -n duapp$i show-mac-throughput-count 5
  done
  date
  sleep 2
done
```

预期结果：持续收取速率日志。

### 3.4 启动 CPU 日志

执行以下命令，并将输出保存到 `D:\test\mobile_automation_platform\ssh_log` 下的 CPU 日志文件：

```bash
while true; do
  top -1 -b -n 1 | head -n 9
  sleep 1
done
```

预期结果：持续收取 CPU 日志。

### 3.5 终端入网

操作终端入网。

预期结果：终端成功入网，终端 IP 为 `10.6.250.2`。

### 3.6 灌包服务器 Ping 终端

在灌包服务器上执行：

```bash
ping 10.6.250.2
```

预期结果：灌包服务器可以 ping 通终端 IP。

### 3.7 执行 RRC Release 操作

在基站 SSH 后台执行以下命令，共执行 3 次，每次间隔 5 秒，并记录每次操作时间：

```bash
odi -n duapp0 display-ue-info | grep Crnti | awk '{print $3}' | xargs -I {} sh -c "odi -n duapp0 release-ue {}"
```

预期结果：操作过程被 RLC/UP 日志、速率日志、CPU 日志记录。

### 3.8 执行 force-rlc-escape-ctrl 操作

在基站 SSH 后台执行以下命令，共执行 3 次，每次间隔 5 秒，并记录每次操作时间：

```bash
odi -n duapp0 display-ue-info | grep Super | awk '{print $3}' | xargs -I {} sh -c "odi -n duapp0 force-rlc-escape-ctrl 1 {}"
```

预期结果：操作过程被 RLC/UP 日志、速率日志、CPU 日志记录。

### 3.9 终端飞行脱网

操作终端进入飞行模式，使终端脱网。

预期结果：终端完成飞行脱网，相关过程被日志记录。

## 4. 测试完成与日志回收

1. 停止 RLC/UP 日志采集。
2. 停止速率日志采集。
3. 停止 CPU 日志采集。
4. 将日志统一保存到：`D:\test\mobile_automation_platform\ssh_log`
5. 停止 Web 抓包。
6. 将 Web 抓包文件保存到电脑。

## 5. 通过标准

- Web 抓包文件已生成，并已保存到电脑。
- RLC/UP 日志、速率日志、CPU 日志三类日志均已生成，并保存到 `D:\test\mobile_automation_platform\ssh_log`。
- RRC release 操作可以在日志中定位到对应时间点和相关记录。
- force-rlc-escape-ctrl 操作可以在日志中定位到对应时间点和相关记录。
- 终端入网状态符合预期：终端成功入网，终端 IP 为 `10.6.250.2`。
- 终端脱网状态符合预期：终端进入飞行模式后完成脱网，日志中可定位对应过程。
