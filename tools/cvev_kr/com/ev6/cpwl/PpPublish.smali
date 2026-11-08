# Leafia CarPlay bridge (Korean EV6): tell the head unit's phone-projection service that a
# wireless CarPlay session is up or over, as stock does for its own wireless sessions and
# as the Korean Ioniq 5 community build (LeafiaProjectionOwner.publish) does:
#   started(1):   getWLDeviceInfo -> requestWLDeviceInfoAdd when there is no record ->
#                 requestWLDeviceReadyStatusUpdate(info, 1) -> requestWLDeviceConnectStatusUpdate(info, 3)
#   finalized(1): requestWLDeviceConnectStatusUpdate(info, 4)
# Without it the car never treated the wireless iPhone as a connected projection device:
# DiPO reached "MainAudio: ENABLE" but the car's AV source never switched to CarPlay, so
# music was silent unless another head-unit source (Melon) happened to be selected.
# Called from CarPlayService.onSessionStarted/onSessionFinalized (cvev_kr/pp-*.hook) with
# the transport (1 = wireless); runs on the bridge's own handler thread.
.class final Lcom/ev6/cpwl/PpPublish;
.super Ljava/lang/Object;
.source "PpPublish.java"

# interfaces
.implements Ljava/lang/Runnable;


# static fields
.field static sLast:Landroid/phoneprojection/WLDeviceInfo;


# instance fields
.field private final addr:Ljava/lang/String;

.field private final op:I


# direct methods
.method constructor <init>(ILjava/lang/String;)V
    .registers 3

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput p1, p0, Lcom/ev6/cpwl/PpPublish;->op:I

    iput-object p2, p0, Lcom/ev6/cpwl/PpPublish;->addr:Ljava/lang/String;

    return-void
.end method

# the iPhone's Bluetooth name, or "iPhone"
.method private static btName(Ljava/lang/String;)Ljava/lang/String;
    .registers 3

    :try_start
    invoke-static {}, Landroid/bluetooth/BluetoothAdapter;->getDefaultAdapter()Landroid/bluetooth/BluetoothAdapter;

    move-result-object v0

    if-eqz v0, :cond_none

    invoke-virtual {v0, p0}, Landroid/bluetooth/BluetoothAdapter;->getRemoteDevice(Ljava/lang/String;)Landroid/bluetooth/BluetoothDevice;

    move-result-object v0

    invoke-virtual {v0}, Landroid/bluetooth/BluetoothDevice;->getName()Ljava/lang/String;

    move-result-object v0

    if-eqz v0, :cond_none

    invoke-virtual {v0}, Ljava/lang/String;->length()I

    move-result v1

    if-eqz v1, :cond_none

    return-object v0
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :cond_none

    :cond_none
    const-string v0, "iPhone"

    return-object v0
.end method

.method static finalized(I)V
    .registers 5

    const/4 v0, 0x1

    if-ne p0, v0, :cond_end

    :try_start
    invoke-static {}, Lcom/ev6/cpwl/Bridge;->handler()Landroid/os/Handler;

    move-result-object v0

    new-instance v1, Lcom/ev6/cpwl/PpPublish;

    const/4 v2, 0x2

    const/4 v3, 0x0

    invoke-direct {v1, v2, v3}, Lcom/ev6/cpwl/PpPublish;-><init>(ILjava/lang/String;)V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :cond_end

    :cond_end
    return-void
.end method

# a new WLDeviceInfo as stock and the Ioniq 5 build make it:
# (address, name, mac, deviceId, user, type 1, transfer 1, false, true, true)
.method private static info(Ljava/lang/String;Ljava/lang/String;I)Landroid/phoneprojection/WLDeviceInfo;
    .registers 14

    new-instance v0, Landroid/phoneprojection/WLDeviceInfo;

    const-string v3, ""

    const-string v4, ""

    const/4 v6, 0x1

    const/4 v7, 0x1

    const/4 v8, 0x0

    const/4 v9, 0x1

    const/4 v10, 0x1

    move-object v1, p0

    move-object v2, p1

    move v5, p2

    invoke-direct/range {v0 .. v10}, Landroid/phoneprojection/WLDeviceInfo;-><init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;IIIZZZ)V

    return-object v0
.end method

.method static started(I)V
    .registers 5

    const/4 v0, 0x1

    if-ne p0, v0, :cond_end

    sget-object v0, Lcom/ev6/cpwl/Bridge;->sAddr:Ljava/lang/String;

    if-nez v0, :cond_post

    const-string v0, "EV6CPWL"

    const-string v1, "PP: no iPhone address, wireless connect not submitted"

    invoke-static {v0, v1}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :cond_end

    :cond_post
    :try_start
    invoke-static {}, Lcom/ev6/cpwl/Bridge;->handler()Landroid/os/Handler;

    move-result-object v1

    new-instance v2, Lcom/ev6/cpwl/PpPublish;

    const/4 v3, 0x1

    invoke-direct {v2, v3, v0}, Lcom/ev6/cpwl/PpPublish;-><init>(ILjava/lang/String;)V

    invoke-virtual {v1, v2}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :cond_end

    :cond_end
    return-void
.end method

# the head unit's user-profile type, as DiPO's own UserProfileManager reports it (0 when the
# unit has no user profiles); DiPO's field is obfuscated: found by its type
.method private static user()I
    .registers 9

    const/4 v8, 0x0

    :try_start
    const-string v0, "com.hkmc.software.user.profile"

    invoke-static {v0}, Lcom/hkmc/Feature;->hasFeature(Ljava/lang/String;)Z

    move-result v0

    if-nez v0, :cond_has

    return v8

    :cond_has
    invoke-static {}, Lcom/daudio/app/dipo/service/DipoService;->bC()Lcom/daudio/app/dipo/service/DipoService;

    move-result-object v0

    if-nez v0, :cond_svc

    return v8

    :cond_svc
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/Class;->getDeclaredFields()[Ljava/lang/reflect/Field;

    move-result-object v1

    array-length v2, v1

    const/4 v3, 0x0

    :goto_loop
    if-ge v3, v2, :cond_none

    aget-object v4, v1, v3

    invoke-virtual {v4}, Ljava/lang/reflect/Field;->getType()Ljava/lang/Class;

    move-result-object v5

    invoke-virtual {v5}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object v5

    const-string v6, "com.hkmc.userprofile.UserProfileManager"

    invoke-virtual {v6, v5}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v5

    if-eqz v5, :cond_next

    const/4 v5, 0x1

    invoke-virtual {v4, v5}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    invoke-virtual {v4, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v4

    if-eqz v4, :cond_next

    check-cast v4, Lcom/hkmc/userprofile/UserProfileManager;

    invoke-virtual {v4}, Lcom/hkmc/userprofile/UserProfileManager;->getUserType()I

    move-result v0

    return v0

    :cond_next
    add-int/lit8 v3, v3, 0x1

    goto :goto_loop
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :cond_none

    :cond_none
    const-string v0, "EV6CPWL"

    const-string v1, "PP: no user profile manager, using user 0"

    invoke-static {v0, v1}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I

    return v8
.end method


# virtual methods
.method public run()V
    .registers 10

    const-string v8, "EV6CPWL"

    :try_start
    const-string v0, "phoneprojection"

    invoke-static {v0}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;

    move-result-object v0

    if-nez v0, :cond_svc

    const-string v1, "PP: no phoneprojection service"

    invoke-static {v8, v1}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I

    return-void

    :cond_svc
    invoke-static {v0}, Landroid/phoneprojection/IPPManager$Stub;->asInterface(Landroid/os/IBinder;)Landroid/phoneprojection/IPPManager;

    move-result-object v0

    iget v1, p0, Lcom/ev6/cpwl/PpPublish;->op:I

    const/4 v2, 0x2

    if-ne v1, v2, :cond_start

    sget-object v1, Lcom/ev6/cpwl/PpPublish;->sLast:Landroid/phoneprojection/WLDeviceInfo;

    if-nez v1, :cond_end

    return-void

    :cond_end
    const/4 v2, 0x4

    invoke-interface {v0, v1, v2}, Landroid/phoneprojection/IPPManager;->requestWLDeviceConnectStatusUpdate(Landroid/phoneprojection/WLDeviceInfo;I)V

    const/4 v1, 0x0

    sput-object v1, Lcom/ev6/cpwl/PpPublish;->sLast:Landroid/phoneprojection/WLDeviceInfo;

    const-string v1, "PP: wireless end submitted"

    invoke-static {v8, v1}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I

    return-void

    :cond_start
    iget-object v1, p0, Lcom/ev6/cpwl/PpPublish;->addr:Ljava/lang/String;

    sget-object v2, Ljava/util/Locale;->US:Ljava/util/Locale;

    invoke-virtual {v1, v2}, Ljava/lang/String;->toUpperCase(Ljava/util/Locale;)Ljava/lang/String;

    move-result-object v1

    invoke-static {}, Lcom/ev6/cpwl/PpPublish;->user()I

    move-result v2

    const-string v3, ""

    invoke-interface {v0, v1, v3, v2}, Landroid/phoneprojection/IPPManager;->getWLDeviceInfo(Ljava/lang/String;Ljava/lang/String;I)Landroid/phoneprojection/WLDeviceInfo;

    move-result-object v4

    if-nez v4, :cond_have

    invoke-static {v1}, Lcom/ev6/cpwl/PpPublish;->btName(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v5

    invoke-static {v1, v5, v2}, Lcom/ev6/cpwl/PpPublish;->info(Ljava/lang/String;Ljava/lang/String;I)Landroid/phoneprojection/WLDeviceInfo;

    move-result-object v6

    invoke-interface {v0, v6}, Landroid/phoneprojection/IPPManager;->requestWLDeviceInfoAdd(Landroid/phoneprojection/WLDeviceInfo;)V

    const-string v7, "PP: wireless device record added"

    invoke-static {v8, v7}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I

    invoke-interface {v0, v1, v3, v2}, Landroid/phoneprojection/IPPManager;->getWLDeviceInfo(Ljava/lang/String;Ljava/lang/String;I)Landroid/phoneprojection/WLDeviceInfo;

    move-result-object v4

    if-nez v4, :cond_have

    const-string v7, "PP: record still missing after the add (the phone-projection app never stored it)"

    invoke-static {v8, v7}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I

    move-object v4, v6

    :cond_have
    const/4 v5, 0x1

    invoke-interface {v0, v4, v5}, Landroid/phoneprojection/IPPManager;->requestWLDeviceReadyStatusUpdate(Landroid/phoneprojection/WLDeviceInfo;I)V

    const/4 v5, 0x3

    invoke-interface {v0, v4, v5}, Landroid/phoneprojection/IPPManager;->requestWLDeviceConnectStatusUpdate(Landroid/phoneprojection/WLDeviceInfo;I)V

    sput-object v4, Lcom/ev6/cpwl/PpPublish;->sLast:Landroid/phoneprojection/WLDeviceInfo;

    new-instance v5, Ljava/lang/StringBuilder;

    invoke-direct {v5}, Ljava/lang/StringBuilder;-><init>()V

    const-string v6, "PP: wireless connected submitted user="

    invoke-virtual {v5, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v5

    invoke-virtual {v5, v2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v5

    invoke-virtual {v5}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v5

    invoke-static {v8, v5}, Lcom/ev6/cpwl/Flog;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    :goto_done
    return-void

    :catch
    move-exception v0

    const-string v1, "PP publish"

    invoke-static {v8, v1, v0}, Lcom/ev6/cpwl/Flog;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    goto :goto_done
.end method
