# FZMM 0.2.21-beta.1：Minecraft 26.2 → 26.3 升级说明

> 基线：`FZMM-Mod 0.2.20`（MC 26.2）
> 目标：MC **26.3**（Mojang 新版号，官方映射，无 Yarn）
> 前置依赖：owo-lib **0.13.1+26.3**（本地构建，官方 maven 暂无 26.3 版）

---

## 零、结论速览

| 验证项 | 结果 |
|---|---|
| `gradle build`（含 `validateAccessWidener`） | **BUILD SUCCESSFUL** |
| `gradle compileJava` | 通过 |
| 9 个 mixin 静态审计 | **0 problems** |
| 注入点描述符逐字节校验 | **全部匹配** |
| 客户端运行（MC 26.3 / SDL 3.4.14 / OpenGL） | 启动、进服正常，**0 个 mixin 应用失败** |
| 独立服务端（MC 26.3） | `Done (0.217s)!` |
| 产物 | `build/libs/fzmm-mc26.3-0.2.21-beta.1.jar` |

本次升级**不是版本号刷新**。26.3 引入了三套底层替换：

| 变更域 | 26.2 | 26.3 |
|---|---|---|
| 窗口 / 输入 | LWJGL **GLFW** | **SDL3**（`org.lwjgl.sdl.*`） |
| 渲染后端 | `com.mojang.blaze3d.*` | `com.mojang.renderpearl.*` |
| 物品数据 | NBT | 数据组件（1.20.5 起，本 mod 26.2 版已是组件体系） |

---

## 一、构建配置改动

### gradle.properties

```diff
-minecraft_version=26.2
-loader_version=0.19.3
+minecraft_version=26.3
+loader_version=0.19.5
-mod_version=0.2.20
+mod_version=0.2.21-beta.1
-fabric_api_version=0.158.0+26.2
+fabric_api_version=0.165.2+26.3
-owo_version=0.13.1+26.2
+owo_version=0.13.1+26.3
-modmenu_version=20.0.1
+modmenu_version=21.0.0
-placeholder_api_version=3.1.0-beta.1+26.2
+placeholder_api_version=3.2.0+26.3
-symbol_chat_version=1.4.2
-symbol_chat_reconfigure_version=0.3.2
+symbol_chat_version=1.4.3
+symbol_chat_reconfigure_version=0.3.3
+lwjgl_version=3.4.3
```

> Loom 保持 `1.17-SNAPSHOT`（实测解析为 1.17.21），对 26.3 可用。

### build.gradle

- 新增 `LocalOwo` 本地仓库源，指向 `./local-maven`
- 新增 `org.lwjgl:lwjgl-tinyfd` 依赖（见第二节）
- 新增 `runs { client / server / clientAuto }`，其中 `clientAuto` 用 quickPlay 自动进本地服
- 依赖版本随 `gradle.properties` 走，无需再改

### fabric.mod.json

```diff
-"minecraft": "~26.2"
+"minecraft": "~26.3"
```

> ⚠️ **不改这一行会直接启动失败**：Fabric 会判定「已安装的 26.3 不满足 ~26.2」并在
> Knot 初始化阶段抛 `FormattedException`，连主菜单都进不去。

---

## 二、依赖 workaround：owo-lib 26.3

官方 maven `io.wispforest:owo-lib` **没有 26.3 版本**，本 mod 使用本地构建的
`owo-lib-0.13.1+26.3.jar` + `owo-sentinel-0.13.1+26.3.jar`，
放在项目内的 `local-maven/` 目录（已加入 `.gitignore`，属构建依赖而非源码）。

```
local-maven/io/wispforest/owo-lib/0.13.1+26.3/
    owo-lib-0.13.1+26.3.jar
    owo-lib-0.13.1+26.3.pom
```

> ⚠️ **本地 pom 必须声明 owo 的传递依赖**，否则编译会报：
>
> ```
> owo-lib-...jar(/io/wispforest/owo/config/Option.class): 错误:
>   无法将类型批注 @org.jetbrains.annotations.Nullable 附加到 Option.endec：
>   找不到io.wispforest.endec.Endec的类文件
> ```
>
> 原因：owo 把 endec / jankson / kdl4j 塞在 jar 的 `META-INF/jars/` 下，
> **嵌套 jar 不会进入消费方的编译类路径**。本地 pom 已照抄官方 26.2 pom 的依赖声明：
>
> | 依赖 | 版本 | scope |
> |---|---|---|
> | `io.wispforest:endec` | 0.1.12 | compile |
> | `io.wispforest.endec:netty` | 0.1.6 | compile |
> | `io.wispforest.endec:gson` | 0.1.7 | compile |
> | `io.wispforest.endec:jankson` | 0.1.7 | compile |
> | `blue.endless:jankson` | 1.2.2 | compile |
> | `com.github.kdl-org:kdl4j` | 1.0.1 | compile |
>
> 同一原因，owo 的注解处理器生成的 `FzmmConfig.java` 会 `import blue.endless.jankson.Jankson;`，
> jankson 同样必须在编译类路径上。

### lwjgl-tinyfd

MC 26.3 的库清单里**没有 `lwjgl-tinyfd`**（26.3 移除了 `lwjgl-glfw`，改用 `lwjgl-sdl`），
而本 mod 的「选择图片文件」「导出资源包」依赖 `org.lwjgl.util.tinyfd.TinyFileDialogs`。
已显式补上：

```groovy
implementation "org.lwjgl:lwjgl-tinyfd:${project.lwjgl_version}"
runtimeOnly "org.lwjgl:lwjgl-tinyfd:${project.lwjgl_version}:natives-windows"
runtimeOnly "org.lwjgl:lwjgl-tinyfd:${project.lwjgl_version}:natives-linux"
runtimeOnly "org.lwjgl:lwjgl-tinyfd:${project.lwjgl_version}:natives-macos"
```

---

## 三、API 迁移清单

### 3.1 输入：GLFW → SDL3

**键码空间整体换了**，不能只做 import 替换：

| 26.2（GLFW） | 值 | 26.3（SDL3，`InputConstants`） | 值 |
|---|---|---|---|
| `GLFW_KEY_Z` | 90 | `InputConstants.KEY_Z` | **29** |
| `GLFW_KEY_Y` | 89 | `InputConstants.KEY_Y` | 28 |
| `GLFW_KEY_ESCAPE` | 256 | `InputConstants.KEY_ESCAPE` | 41 |
| `GLFW_MOUSE_BUTTON_LEFT` | 0 | `InputConstants.MOUSE_BUTTON_LEFT` | **1** |
| `GLFW_MOUSE_BUTTON_1` | 0 | `InputConstants.MOUSE_BUTTON_LEFT` | 1 |

同时 **`InputConstants.Type.KEYSYM` 在 26.3 已被移除**，`Type` 只剩 `KEYBOARD` / `MOUSE`：

```diff
-new KeyMapping("key.fzmm.mainGui", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_Z, KEY_CATEGORY);
+new KeyMapping("key.fzmm.mainGui", InputConstants.Type.KEYBOARD, InputConstants.KEY_Z, KEY_CATEGORY);
```

涉及文件：`FzmmClient`、`HistoryClipboard`、`BaseFzmmScreen`、`SuggestionTextBox`、`HeadGalleryScreen`。

### 3.2 打开文件 / 文件夹

`net.minecraft.util.OS` 类**整体消失**，`Util.getPlatform()` 也一并没了。
26.3 统一走 `com.mojang.blaze3d.Blaze3D`：

```diff
-Util.getPlatform().openFile(SKIN_SAVE_FOLDER_PATH.toFile());
+Blaze3D.openPath(SKIN_SAVE_FOLDER_PATH);
```

涉及文件：`HeadGeneratorScreen`、`HeadComponentOverlay`。

### 3.3 打开外部链接

`ConfirmLinkScreen.confirmLinkNow` 的第二个参数由 `String` 改为 `java.net.URI`：

```diff
-ConfirmLinkScreen.confirmLinkNow(screen, FzmmWikiConstants.HEAD_GENERATOR_WIKI_LINK, true);
+ConfirmLinkScreen.confirmLinkNow(screen, URI.create(FzmmWikiConstants.HEAD_GENERATOR_WIKI_LINK), true);
```

涉及文件：`EncryptBookScreen`、`HeadGalleryScreen`、`HeadGeneratorScreen`、`PlayerStatueScreen`、
`TextFormatPlaceholderApiTab`。

### 3.4 容器内容

`ItemContainerContents.allItemsCopyStream()` 更名为 `nonEmptyItemCopyStream()`：

```diff
-result.allItemsCopyStream().toList();
+result.nonEmptyItemCopyStream().toList();
```

涉及文件：`InventoryUtils`、`RefillContainer`。

> 26.3 的 `ItemContainerContents` 内部存储已改为 `ItemStackTemplate`，
> `nonEmptyItemCopyStream()` 返回的仍是 `Stream<ItemStack>`，语义一致。

### 3.5 头颅 Profile（authlib 10.0.77）

`com.mojang.authlib.yggdrasil` 包**整体迁移到 `com.mojang.authlib.services`**：

| 26.2 | 26.3 |
|---|---|
| `com.mojang.authlib.yggdrasil.ProfileResult` | `com.mojang.authlib.services.ProfileResult` |
| `com.mojang.authlib.yggdrasil.response.NameAndId` | `com.mojang.authlib.services.response.NameAndId` |

`GameProfile` / `Property` / `PropertyMap` / `MinecraftProfileTexture` 位置不变。

> MC 26.3 的 `net.minecraft.server.Services` 记录也重构了（新增 `profileResolver`、
> `nameToIdCache`），但本 mod 用到的 `profileRepository()` 与 `sessionService()` 入口未变，
> 因此 `VanillaSkinGetter` **只需改 import**。

---

## 四、Mixin 改动（关键）

### 4.1 GameRenderer.renderItemInHand 签名变了 —— 不改会启动即崩

26.3 的渲染层迁移到 renderpearl 后，`renderItemInHand` 的第三个参数
由 JOML 的 `Matrix4fc` 换成了 renderpearl 的 `GpuTextureView`：

```diff
-@Inject(method = "renderItemInHand(Lnet/minecraft/client/renderer/state/level/CameraRenderState;FLorg/joml/Matrix4fc;)V",
-        at = @At("HEAD"), cancellable = true)
-private void fzmm$removeHandInScreenshotHud(CameraRenderState cameraState, float deltaPartialTick, Matrix4fc modelViewMatrix, CallbackInfo ci) {
+@Inject(method = "renderItemInHand(Lnet/minecraft/client/renderer/state/level/CameraRenderState;Lnet/minecraft/client/renderer/state/level/PlayerRenderState;Lcom/mojang/renderpearl/api/textures/GpuTextureView;)V",
+        at = @At("HEAD"), cancellable = true)
+private void fzmm$removeHandInScreenshotHud(CameraRenderState cameraState, PlayerRenderState playerState, GpuTextureView textureView, CallbackInfo ci) {
```

> ⚠️ 描述符形式的 `method =` **只比对方法名会漏掉这种破坏**。本项目为此补了一个
> 逐字节校验脚本（见第五节）。

### 4.2 其余 8 个 mixin 无需改动

`@Mixin` 目标、`@Inject` 方法名、`@Shadow` 成员、`@Accessor` 目标在 26.3 全部保持有效：

| Mixin | 目标 | 结论 |
|---|---|---|
| `MultiLineEditBoxMixin` | `MultiLineEditBox` | `textColor` / `cursorColor` 仍是 `private final int` |
| `MultilineTextFieldAccessor` | `MultilineTextField` | `getWidth()` 访问器对应字段 `width`，仍在 |
| `ItemFrameRendererMixin` | `ItemFrameRenderer` | `extractRenderState` 描述符未变 |
| `ItemDisplayParametersMixin` | `CreativeModeTab.ItemDisplayParameters` | `needsUpdate` 描述符未变 |
| `CreativeInventoryScreenMixin` | `CreativeModeInventoryScreen` | `displayOperatorCreativeTab` 仍是 `private final boolean` |
| `EditBoxMixin` | `EditBox` | `insertText` / `charTyped` 描述符未变 |
| `ChatScreenMixin` | `ChatScreen` | `onEdited` / `moveInHistory` / `normalizeChatMessage` 描述符未变 |
| `ChatComponentMixin` | `ChatComponent` | `extractRenderState` 描述符未变 |

---

## 五、验证工具

项目 `tools/` 下新增三个脚本，均不需要启动游戏：

| 脚本 | 作用 |
|---|---|
| `audit_mixins_263.py` | 校验每个 mixin 的 `@Mixin` 目标类、`@Inject`/`@ModifyReturnValue` 目标方法、`@Shadow` 成员、`@Accessor` 目标是否存在于 26.3 |
| `check_injection_descriptors.py` | 对**描述符形式**的注入点做逐字节匹配（方法名比对会漏掉签名变化） |
| `find_method_owner.py` | 在 MC jar 里反查某个方法名出现在哪些类里（用于 API 搬家时定位） |

```powershell
python tools\audit_mixins_263.py            # exit 0 = 全部通过
python tools\check_injection_descriptors.py  # exit 0 = 全部匹配
```

另有 `tools/run-server.cmd` / `tools/run-client.cmd` / `tools/launch_test_env.ps1`
用于拉起 26.3 的服务端与客户端（`clientAuto` 用 `--quickPlayMultiplayer` 自动进服）。

> ⚠️ MC 26.3 **重命名了 quickPlay 参数**：`--quickPlay multiplayer <addr>` 已失效，
> 现在是 `--quickPlayMultiplayer <addr>`。用旧写法会看到日志
> `Completely ignored arguments: [--quickPlay, multiplayer, ...]` 而不自动进服。

---

## 六、已知问题 / 注意事项

1. **owo-lib 自身的 mixin 分段问题（上游缺陷，非本 mod）**
   owo 把客户端 mixin（`braid.MinecraftAccessor`、`braid.RenderTypeInvoker`、
   `braid.ClickableStyleFinderAccessor`）放进了通用 mixin 段，服务端加载时会刷：
   ```
   [main/WARN] (FabricLoader/Mixin) @Mixin target net.minecraft.client.Minecraft was not found
   ```
   服务端照常启动，不影响 FZMM。

2. **`old_give` 版本表已补齐**
   `VersionArgumentType#initVersions` 原本最高只到 `26.1`，26.2 那行是被注释掉的
   （`// result.add(new Pair<>("26.2", 4903));`）——上游自己发布 26.2 版时漏了。
   现已补上 `26.3 → 5023`、`26.2 → 4903`（data version 取自 MC jar 内的 `version.json`
   的 `world_version`）。

3. **仍需实机验证的部分**
   编译通过 ≠ mixin 变换通过 ≠ 渲染正确。本次已验证「启动、进服、0 mixin 失败」，
   但 **Vulkan 路径未验证**（本机测试用的是 OpenGL），renderpearl 的 Vulkan 行为需另行确认。

---

## 七、上游参考

- owo-lib 的同批移植分析：`../owo-lib-0.13.1-26.2/UPGRADE_26_3.md`
- owo-lib 的实机测试指南：`../owo-lib-0.13.1-26.2/TESTING_26_3.md`
- 上游 PR：`https://github.com/wisp-forest/owo-lib/pull/501`、`/pull/500`
