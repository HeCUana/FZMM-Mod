package fzmm.zailer.me.mixin.screenshot_hud;

import fzmm.zailer.me.client.gui.components.image.source.ScreenshotSource;
import com.mojang.renderpearl.api.textures.GpuTextureView;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.renderer.state.level.CameraRenderState;
import net.minecraft.client.renderer.state.level.PlayerRenderState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(GameRenderer.class)
public abstract class GameRendererMixin {

    @Inject(method = "renderItemInHand(Lnet/minecraft/client/renderer/state/level/CameraRenderState;Lnet/minecraft/client/renderer/state/level/PlayerRenderState;Lcom/mojang/renderpearl/api/textures/GpuTextureView;)V", at = @At("HEAD"), cancellable = true)
    private void fzmm$removeHandInScreenshotHud(CameraRenderState cameraState, PlayerRenderState playerState, GpuTextureView textureView, CallbackInfo ci) {
        if (ScreenshotSource.hasInstance()) {
            ci.cancel();
        }
    }
}
