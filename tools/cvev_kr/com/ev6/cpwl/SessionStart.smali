# Leafia CarPlay bridge (Korean EV6): start DiPO's CarPlay session for the Bluetooth iAP2
# session, as DiPO does itself when its own iAP2 listener gets TransportIdentifier:
# DipoService.bC().fH (e/b) .G() (e/n, service/q) .n(addr) = onTransportIdentifier(addr)
# -> startCarPlaySession() (DipoService.I) -> createDipo/startDipo, which opens the
# receiver the iPhone joins over Wi-Fi. On Korean V039 that notification never reaches
# DiPO for the Bluetooth session (and ro.product.opt.stepofspec >= 0 keeps createDipo
# from starting the receiver on its own), so nothing listened. Posted on DiPO's main
# thread by TxListener; fields and methods are private and obfuscated: reflection.
# Before that, createDipo (DipoService.bO) and updateInitAppState (DipoService.eJ), as
# createDipo does for a car whose stepofspec is below 0 and the wired path does after
# authentication: eJ sets the initial screen/main-audio ownership. Without it the iPhone
# owned the main audio from the start ("permMainAudio controller"), DiPO never saw main
# audio change hands, never asked for the CarPlay media source, and music played only
# while the car's AV source happened to share the head unit's own output (e.g. Melon).
.class final Lcom/ev6/cpwl/SessionStart;
.super Ljava/lang/Object;
.source "SessionStart.java"

# interfaces
.implements Ljava/lang/Runnable;


# instance fields
.field private final addr:Ljava/lang/String;


# direct methods
.method constructor <init>(Ljava/lang/String;)V
    .registers 2

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/ev6/cpwl/SessionStart;->addr:Ljava/lang/String;

    return-void
.end method

# obj's private no-argument method `name` (logs, never throws)
.method private static call(Ljava/lang/Object;Ljava/lang/String;)V
    .registers 6

    :try_start
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v0

    const/4 v1, 0x0

    new-array v1, v1, [Ljava/lang/Class;

    invoke-virtual {v0, p1, v1}, Ljava/lang/Class;->getDeclaredMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v0

    const/4 v1, 0x1

    invoke-virtual {v0, v1}, Ljava/lang/reflect/Method;->setAccessible(Z)V

    const/4 v1, 0x0

    new-array v1, v1, [Ljava/lang/Object;

    invoke-virtual {v0, p0, v1}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    :goto_end
    return-void

    :catch
    move-exception v0

    const-string v1, "EV6CPWL"

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "DiPO: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    goto :goto_end
.end method


# virtual methods
.method public run()V
    .registers 8

    :try_start
    invoke-static {}, Lcom/daudio/app/dipo/service/DipoService;->bC()Lcom/daudio/app/dipo/service/DipoService;

    move-result-object v0

    if-eqz v0, :cond_none

    const-string v1, "bO"

    invoke-static {v0, v1}, Lcom/ev6/cpwl/SessionStart;->call(Ljava/lang/Object;Ljava/lang/String;)V

    const-string v1, "eJ"

    invoke-static {v0, v1}, Lcom/ev6/cpwl/SessionStart;->call(Ljava/lang/Object;Ljava/lang/String;)V

    const-string v1, "EV6CPWL"

    const-string v2, "DiPO: createDipo + updateInitAppState done"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v1

    const-string v2, "fH"

    invoke-virtual {v1, v2}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v1

    const/4 v2, 0x1

    invoke-virtual {v1, v2}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    invoke-virtual {v1, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    if-eqz v0, :cond_none

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v1

    const-string v2, "G"

    const/4 v3, 0x0

    new-array v3, v3, [Ljava/lang/Class;

    invoke-virtual {v1, v2, v3}, Ljava/lang/Class;->getDeclaredMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v1

    const/4 v2, 0x1

    invoke-virtual {v1, v2}, Ljava/lang/reflect/Method;->setAccessible(Z)V

    const/4 v3, 0x0

    new-array v3, v3, [Ljava/lang/Object;

    invoke-virtual {v1, v0, v3}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    if-eqz v0, :cond_none

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v1

    const-string v2, "n"

    const/4 v3, 0x1

    new-array v3, v3, [Ljava/lang/Class;

    const-class v4, Ljava/lang/String;

    const/4 v5, 0x0

    aput-object v4, v3, v5

    invoke-virtual {v1, v2, v3}, Ljava/lang/Class;->getDeclaredMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v1

    const/4 v2, 0x1

    invoke-virtual {v1, v2}, Ljava/lang/reflect/Method;->setAccessible(Z)V

    const/4 v3, 0x1

    new-array v3, v3, [Ljava/lang/Object;

    iget-object v4, p0, Lcom/ev6/cpwl/SessionStart;->addr:Ljava/lang/String;

    aput-object v4, v3, v5

    invoke-virtual {v1, v0, v3}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    const-string v0, "EV6CPWL"

    const-string v1, "DiPO: onTransportIdentifier for the Bluetooth session done"

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    :goto_end
    return-void

    :cond_none
    const-string v0, "EV6CPWL"

    const-string v1, "DiPO: not ready, CarPlay session not started"

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_end

    :catch
    move-exception v0

    const-string v1, "EV6CPWL"

    const-string v2, "DiPO: onTransportIdentifier"

    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    goto :goto_end
.end method
