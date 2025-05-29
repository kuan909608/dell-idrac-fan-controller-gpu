[English](README.md) | [繁體中文](README_zh-TW.md)

# Dell R730 風扇控制腳本（繁體中文版）

> 一套以溫度為基準的 Dell 伺服器風扇自動控制腳本（已在 R730 測試，應適用多數 PowerEdge 機型），支援本機與遠端主機。

- [需求環境](#需求環境)
- [安裝／升級](#安裝升級)
  - [Docker 部署](#docker-部署)
- [設定說明](#設定說明)
- [運作邏輯](#運作邏輯)
- [多主機與 VM 支援](#多主機與-vm-支援)
- [遠端主機注意事項](#遠端主機注意事項)
- [致謝](#致謝)

---

## 需求環境

1. 已安裝 Python 3。
2. 所有 iDRAC 已啟用 **IPMI Over LAN**（登入 iDRAC > Network/Security > IPMI Settings）。
   - 僅管理本機時可不啟用。
3. 所有需要被監測溫度的主機，請依需求安裝對應的感測工具：

   - 監測本機 CPU：需安裝並設定 `lm-sensors`
   - 監測 NVIDIA GPU：需安裝 `nvidia-smi`
   - 監測 AMD GPU：需安裝 `rocm-smi`

   - 雙 CPU 範例輸出：

     ```text
     coretemp-isa-0000
     Adapter: ISA adapter
     Core 0:       +38.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 1:       +46.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 2:       +40.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 8:       +43.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 9:       +39.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 10:      +39.0°C  (high = +69.0°C, crit = +79.0°C)

     coretemp-isa-0001
     Adapter: ISA adapter
     Core 0:       +29.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 1:       +35.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 2:       +29.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 8:       +34.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 9:       +33.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 10:      +31.0°C  (high = +69.0°C, crit = +79.0°C)
     ```

## 安裝／升級

請以 root 權限執行安裝腳本：

```bash
git clone https://github.com/kuan909608/dell-idrac-fan-controller-gpu.git
cd dell-idrac-fan-controller-gpu
sudo ./install.sh [<安裝路徑>]
```

預設安裝路徑為 `/opt/fan_control`，服務名稱為 `fan-control.service`。若已有設定檔，會自動備份為 `.old`。

### Docker 部署

如需以 Docker 管理遠端主機，請自行掛載 YAML 設定檔與 SSH 金鑰資料夾：

```bash
docker build -t fan_control .
docker run -d --restart=always --name fan_control -v "./fan_control.yaml:/app/fan_control.yaml:ro" -v "./keys:/app/keys:ro" fan_control
```

建議於正式環境搭配 Orchestrator 使用。

---

### 部屬方式選擇指南

本工具支援兩種部屬方式：systemd（裸機）與 Docker。**同一台主機請僅選擇一種方式，不可同時啟用。**

#### 何時選擇 systemd（裸機）

- 需要直接存取本機硬體感測器（如 lm-sensors）時建議使用。
- 適合希望服務隨作業系統自動啟動並由 systemd 管理的環境。
- `install.sh` 會自動安裝依賴、建立 venv、複製檔案並設定 systemd 服務。

#### 何時選擇 Docker

- 僅需遠端管理，或希望隔離執行環境、方便移植時建議使用。
- 若需在 Docker 內存取本機硬體感測器，必須額外掛載系統目錄，例如：
  ```bash
  docker run ... -v /dev:/dev -v /sys:/sys ...
  ```
- 請務必掛載設定檔與 SSH 金鑰資料夾（如上方範例）。
- 正式環境建議搭配 Orchestrator 增加可靠性。

#### 注意事項

- **請勿同時啟用 systemd 服務與 Docker container，否則可能產生衝突或資源競爭。**
- `install.sh` 會覆蓋現有檔案與 systemd 服務，執行前請先備份設定。
- Docker 內使用 SSH 金鑰時，請注意權限與安全性管理。

## 設定說明

請編輯安裝目錄下的 `fan_control_config.yaml` 進行設定。

### 設定檔結構

- `general`：全域參數
- `hosts`：主機清單，每台主機可自訂溫度門檻、風速、認證資訊、GPU 類型與 VM

#### general 區塊

| 參數名稱                         | 說明                                                   |
| -------------------------------- | ------------------------------------------------------ |
| `debug`                          | 除錯模式（僅顯示指令不執行，並輸出詳細日誌）           |
| `interval`                       | 每次溫度檢查與風扇調整的間隔秒數                       |
| `temperature_control_mode`       | 風扇控制依據，`max` 代表取最高溫，`avg` 代表取平均溫度 |
| `cpu_temperature_command`        | 取得 CPU 溫度的 shell 指令（以分號分隔）               |
| `gpu_temperature_command_nvidia` | 取得 NVIDIA GPU 溫度的 shell 指令（以分號分隔）        |
| `gpu_temperature_command_amd`    | 取得 AMD GPU 溫度的 shell 指令（以分號分隔）           |

#### hosts 區塊

| 參數名稱           | 說明                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `name`             | 主機名稱                                                                                      |
| `fan_control_mode` | 風扇控制模式，`manual` 由腳本控制，`automatic` 由硬體自動控制                                 |
| `temperatures`     | 溫度門檻（°C），需與 speeds 成對，**必須至少 2 組**，數量不限                                 |
| `speeds`           | 對應風扇轉速（%），需與 temperatures 成對，**必須至少 2 組**，數量不限                        |
| `hysteresis`       | 遲滯值，避免頻繁切換風速（°C），建議小於任兩組相鄰溫度門檻的差值                              |
| `ipmi_credentials` | （選填）本機 IPMI 登入資訊                                                                    |
| `ssh_credentials`  | （選填）本機 SSH 登入資訊，支援 `host`、`username`、`password`，可選填 `key_path`（私鑰路徑） |
| `gpu_type`         | （選填）支援的 GPU 類型，可為字串（如 `nvidia`）或陣列（如 `[nvidia, amd]`）                  |
| `vms`              | （選填）VM 清單，每台 VM 可自訂 SSH 認證與 GPU 類型，詳見下方 vms 物件說明                    |

##### vms 物件

每個 VM 物件支援以下欄位：

| 欄位名稱          | 說明                                                                                   |
| ----------------- | -------------------------------------------------------------------------------------- |
| `name`            | VM 名稱                                                                                |
| `ssh_credentials` | VM 的 SSH 登入資訊，支援 `host`、`username`、`password`，可選填 `key_path`（私鑰路徑） |
| `gpu_type`        | 支援的 GPU 類型，可為字串（如 `nvidia`）或陣列（如 `[nvidia, amd]`）                   |

##### 自動分割溫度門檻與風速

若只設定 2 組 `temperatures` 與 `speeds`（如 `[40, 80]` 與 `[20, 80]`），系統會依據 `hysteresis` 自動分割成多組門檻與風速。

分割邏輯：

- 以 `hysteresis * 2` 為間距，從最低溫到最高溫自動切分。
- 每個區間都會產生一組新的門檻與對應風速，讓風扇轉速調整更平滑。

**範例：**

```yaml
temperatures: [40, 80]
speeds: [20, 80]
hysteresis: 5
```

會自動展開為：

```
thresholds: [40.00, 50.00, 60.00, 70.00, 80.00]
speeds: [20, 35, 50, 65, 80]
```

##### 範例

```yaml
general:
  debug: False
  interval: 60
  cpu_temperature_command: "sensors | grep -E 'Core [0-9]+:' | awk '{print $3}' | sed 's/+//;s/°C//' | paste -sd ';' -"
  gpu_temperature_command_nvidia: "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | paste -sd ';' -"
  gpu_temperature_command_amd: "rocm-smi --showtemp | grep -E 'Temp' | awk '{print \$2}' | sed 's/[^0-9.]//g' | paste -sd ';' -"

hosts:
  - name: host1
    temperatures: [40, 60, 80]
    speeds: [20, 50, 80]
    hysteresis: 5
    ipmi_credentials:
      host: 10.0.0.1
      username: admin
      # 密碼登入範例
      password: password
      # 金鑰登入範例（建議將私鑰檔案放在 keys/ 資料夾下）
      # key_path: /app/keys/id_rsa
    ssh_credentials:
      host: 10.0.0.2
      username: admin
      password: password
    gpu_type: nvidia
    vms:
      - name: vm1
        ssh_credentials:
          host: 10.0.0.3
          username: user
          password: password
        gpu_type: nvidia
  - name: host2
    temperatures: [35, 55, 75]
    speeds: [30, 60, 90]
    hysteresis: 5
    gpu_type: nvidia
```

##### 自動分割溫度門檻與風速

若只設定 2 組 `temperatures` 與 `speeds`（如 `[40, 80]` 與 `[20, 80]`），系統會依據 `hysteresis` 自動分割成多組門檻與風速。

分割邏輯：

- 以 `hysteresis * 2` 為間距，從最低溫到最高溫自動切分。
- 每個區間都會產生一組新的門檻與對應風速，讓風扇轉速調整更平滑。

**範例：**

```yaml
temperatures: [40, 80]
speeds: [20, 80]
hysteresis: 5
```

會自動展開為：

```
thresholds: [40.00, 50.00, 60.00, 70.00, 80.00]
speeds: [20, 35, 50, 65, 80]
```

## 運作邏輯

每隔 `interval` 秒，腳本會取得所有主機及其 VM 的 CPU/GPU 溫度。  
以所有 CPU/GPU（含 VM）最高溫度作為控制依據，決定風扇轉速。

- 若溫度資料異常，風扇將以設定中的最高速（speeds 最後一個值）運轉以保護硬體。
- 風扇轉速依據每組門檻與對應百分比自動切換，超過最高門檻時風扇會固定在最高速（設定中的最大百分比）。
- 所有溫度與控制紀錄皆會寫入狀態，方便日後追蹤與除錯。

| 條件                             | 風扇轉速             |
| -------------------------------- | -------------------- |
| _Tmax_ ≤ Threshold1              | Speed1               |
| Threshold1 < _Tmax_ ≤ Threshold2 | Speed2               |
| ...                              | ...                  |
| _Tmax_ > ThresholdN              | 最高速（最大百分比） |

若有設定 `hysteresis`，當溫度下降時，必須低於該門檻值減去 hysteresis 才會降低風扇轉速。  
例如：Threshold2 設為 37°C，hysteresis 設為 3°C，則風扇不會從 Threshold3 轉速降到 Threshold2，直到溫度降到 34°C。

## 遠端主機注意事項

本控制器也能監控遠端主機的溫度並調整風扇轉速：唯一需要注意的是，必須透過外部指令取得溫度資料，例如 SSH。控制器預期該指令回傳**可被解析為浮點數的換行分隔數字清單**。

**內建範例適用於遠端 Proxmox VE 主機**：會透過 SSH 連線並取得所有 CPU core 的溫度，每行一個數字。這樣就能像管理本機一樣管理該主機，無需對作業系統做難以追蹤的修改。

## 致謝

特別感謝 [NoLooseEnds 的指引](https://github.com/NoLooseEnds/Scripts/tree/master/R710-IPMI-TEMP) 提供核心指令、[sulaweyo 的 ruby 腳本](https://github.com/sulaweyo/r710-fan-control) 提供自動化靈感，以及本專案 fork 自 [nmaggioni 的 r710-fan-controller](https://github.com/nmaggioni/r710-fan-controller)。

**注意：** 本腳本與其他方案的主要差異（除了支援遠端主機外），在於它是根據 CPU core 溫度控制，而非主機板上的環境溫度感測器。
