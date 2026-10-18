# lang-CPP-SYSTEMS — Modern C/C++ (C++20/23), Embedded Firmware (ESP32/STM32) & WebAssembly

Use when writing or reviewing C, Modern C++ (C++17/20/23), CMake build configurations, embedded/IoT firmware
(ESP32, STM32, FreeRTOS, Arduino/ESP-IDF), native Node/Python/FFI extensions, or WebAssembly (Wasm) modules.

## 1. Modern C++ (C++20/23) memory & resource safety (RAII)

- **Zero raw owning pointers**:
  - Never write naked `new`, `delete`, `malloc`, or `free` in application code.
  - Use `std::unique_ptr<T>` (`std::make_unique`) for exclusive ownership, `std::shared_ptr<T>` (`std::make_shared`)
    only when shared lifetime is genuinely required, and references (`T&` / `const T&`) or raw pointers (`T*`) strictly
    for non-owning observation when lifetime is guaranteed to outlive the callee.
- **Rule of Zero / Rule of Five**:
  - Prefer the **Rule of Zero**: compose classes from standard RAII types (`std::string`, `std::vector`, `std::unique_ptr`)
    so you write no custom destructor, copy, or move operators.
  - If a class directly wraps a raw OS/C handle (socket, file descriptor, `sqlite3*`, mutex), follow the **Rule of Five**:
    delete copy operations (`= delete`) and implement move constructor + move assignment explicitly.
- **Bounds-safe views over C-arrays**:
  - Use `std::span<const std::byte>` / `std::span<T>` instead of `(T* ptr, size_t len)` pairs.
  - Use `std::string_view` for read-only string parameters (never return a `string_view` pointing to a temporary local `std::string`!).
  - Never use unsafe C string functions (`strcpy`, `strcat`, `sprintf`, `gets`); use `std::format` / `snprintf` with explicit bounds.

## 2. Type safety, error handling & concurrency

- **Strict compiler warnings & sanitizers**:
  - Compile with `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror` (GCC/Clang) or `/W4 /WX` (MSVC).
  - Run tests under **AddressSanitizer (`-fsanitize=address`)**, **UndefinedBehaviorSanitizer (`-fsanitize=undefined`)**,
    and **ThreadSanitizer (`-fsanitize=thread`)** in CI.
- **Explicit types & casts**:
  - Use fixed-width integers (`uint8_t`, `int32_t`, `uint64_t`, `size_t`) from `<cstdint>` for wire protocols, binary files, and hardware registers.
  - Never use C-style casts `(Foo*)bar` — use `static_cast` for checked conversions and avoid `reinterpret_cast` / `const_cast` outside low-level hardware/serialization boundaries.
  - Use `std::optional<T>` for nullable values and `std::expected<T, Error>` (C++23) or `[[nodiscard]]` status results for expected failures.
- **Concurrency**: use `std::jthread` (auto-joining + `std::stop_token` cooperative cancellation), `std::scoped_lock` for
  mutexes, and `std::atomic<T>` with explicit memory ordering. Never access shared mutable state across threads without synchronization.

## 3. Modern `CMakeLists.txt` authoring rules

- **Target-based CMake (3.20+)**: never use global `include_directories()`, `add_definitions()`, or `link_libraries()`.
- Always scope properties per target with explicit visibility (`PRIVATE`, `PUBLIC`, `INTERFACE`):
  ```cmake
  cmake_minimum_required(VERSION 3.24)
  project(my_service VERSION 1.0.0 LANGUAGES CXX)

  add_executable(my_service src/main.cpp src/engine.cpp)
  target_compile_features(my_service PRIVATE cxx_std_20)
  target_include_directories(my_service PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include")
  target_link_libraries(my_service PRIVATE fmt::fmt Threads::Threads)
  ```

## 4. Embedded Firmware (ESP32 / STM32 / FreeRTOS) rules

- **Deterministic memory (zero dynamic heap fragmentation in loop)**:
  - Allocate buffers statically or once during `setup()` / boot initialization. Avoid `String` concatenation or repeated
    `malloc`/`new` inside the main loop or FreeRTOS tasks on microcontrollers with limited SRAM.
- **ISR (Interrupt Service Routine) discipline**:
  - Keep ISRs tiny and fast (set a `volatile` flag or push to a FreeRTOS queue via `xQueueSendFromISR`).
  - **NEVER** call blocking functions (`delay`, `vTaskDelay`, `Serial.print`, I2C/SPI transfers, mutex locks, or heap allocation) inside an ISR.
  - On ESP32, mark ISR functions and constants accessed while flash cache is disabled with `IRAM_ATTR` / `DRAM_ATTR`.
- **Hardware Watchdog & Brownout resilience**:
  - Enable the Task Watchdog Timer (`esp_task_wdt`) so deadlocked tasks trigger a clean reboot.
  - Use wear-leveled NVS / LittleFS with atomic rename/CRC32 checks so power loss mid-write never bricks device configuration.
