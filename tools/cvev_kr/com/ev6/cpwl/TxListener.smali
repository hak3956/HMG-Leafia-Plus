# Leafia CarPlay bridge: iAP2 listener for the external Bluetooth / CarPlay transports.
# Written again for the Korean EV6 port (tools/bridgeport.py --replace): the bridge build
# rebuilt from this car's files had disconnected() cut short and notify() missing.
# Bridge.onIap2Bound registers it with Iap2SvcInit(..., support type 0xc00 =
# LISTENER_EXTERNAL_BT_TRANSPORT 0x400 | LISTENER_EXTERNAL_CARPLAY_TRANSPORT 0x800).
#   connected(comp)     as the original: USB CarPlay (1) marks sUsb, CarPlay client (5)
#                       lets Bridge flush what it buffered
#   disconnected(comp)  USB CarPlay gone: clear sUsb (the only place that does) and let
#                       Bridge go back to Bluetooth (onUsbGone, a no-op without an iPhone)
#   notify(noti, ...)   0x50: iAP2 bytes for the iPhone over Bluetooth -> Bridge.writeSpp
#                       0x51: iAP2 bytes for the CarPlay channel       -> Bridge.writeCp
#                       the bytes are the message's blob item (OBJ_BLOB 0xb; the first
#                       item is the component number, an int)
.class final Lcom/ev6/cpwl/TxListener;
.super Lcom/tcc/iap2/IIap2Listener$Stub;
.source "TxListener.java"


# static fields
.field static final COMPONENT_USB_CARPLAY:I = 0x1

.field static final NOTI_BT_TRANSPORT_DATA:I = 0x50

.field static final NOTI_CARPLAY_CLIENT_TRANSPORT_DATA:I = 0x51

.field static final OBJ_BLOB:I = 0xb


# direct methods
.method constructor <init>()V
    .registers 1

    invoke-direct {p0}, Lcom/tcc/iap2/IIap2Listener$Stub;-><init>()V

    return-void
.end method

# the first non-empty byte array among the message's items, or null
.method private static blob(Lcom/tcc/iap2/Iap2NotiMsg;)[B
    .registers 6

    if-nez p0, :cond_have

    const/4 v4, 0x0

    return-object v4

    :cond_have
    invoke-virtual {p0}, Lcom/tcc/iap2/Iap2NotiMsg;->getItemGroup()Lcom/tcc/iap2/Iap2NotiMsg$Iap2ObjGroup;

    move-result-object v0

    if-eqz v0, :cond_none

    invoke-virtual {v0}, Lcom/tcc/iap2/Iap2NotiMsg$Iap2ObjGroup;->getItemCnt()I

    move-result v1

    const/4 v2, 0x0

    :goto_loop
    if-ge v2, v1, :cond_none

    invoke-virtual {v0, v2}, Lcom/tcc/iap2/Iap2NotiMsg$Iap2ObjGroup;->getObjItem(I)Lcom/tcc/iap2/Iap2NotiMsg$Iap2ObjItem;

    move-result-object v3

    if-eqz v3, :cond_next

    invoke-virtual {v3}, Lcom/tcc/iap2/Iap2NotiMsg$Iap2ObjItem;->getItemByteArray()[B

    move-result-object v3

    if-eqz v3, :cond_next

    array-length v4, v3

    if-lez v4, :cond_next

    return-object v3

    :cond_next
    add-int/lit8 v2, v2, 0x1

    goto :goto_loop

    :cond_none
    const/4 v4, 0x0

    return-object v4
.end method


# virtual methods
.method public connected(ILjava/lang/String;)V
    .registers 7

    const/4 v3, 0x1

    const-string v0, "EV6CPWL"

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "iAP2 connected comp="

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    if-ne p1, v3, :cond_1e

    sput-boolean v3, Lcom/ev6/cpwl/Bridge;->sUsb:Z

    :cond_1d
    :goto_1d
    return-void

    :cond_1e
    const/4 v0, 0x5

    if-ne p1, v0, :cond_1d

    invoke-static {}, Lcom/ev6/cpwl/Bridge;->onCpClientConnected()V

    goto :goto_1d
.end method

.method public disconnected(I)V
    .registers 6

    :try_start
    const-string v0, "EV6CPWL"

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "iAP2 disconnected comp="

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    const/4 v0, 0x1

    if-ne p1, v0, :cond_end

    const/4 v0, 0x0

    sput-boolean v0, Lcom/ev6/cpwl/Bridge;->sUsb:Z

    invoke-static {}, Lcom/ev6/cpwl/Bridge;->onUsbGone()V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    :cond_end
    return-void

    :catch
    move-exception v0

    const-string v1, "EV6CPWL"

    const-string v2, "disconnected"

    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    goto :cond_end
.end method

.method public notify(IIILcom/tcc/iap2/Iap2NotiMsg;)V
    .registers 10

    const/16 v0, 0x50

    if-eq p1, v0, :cond_data

    const/16 v0, 0x51

    if-eq p1, v0, :cond_data

    :goto_end
    return-void

    :cond_data
    :try_start
    invoke-static {p4}, Lcom/ev6/cpwl/TxListener;->blob(Lcom/tcc/iap2/Iap2NotiMsg;)[B

    move-result-object v1

    if-eqz v1, :goto_end

    const/16 v0, 0x50

    if-ne p1, v0, :cond_cp

    invoke-static {v1}, Lcom/ev6/cpwl/Bridge;->writeSpp([B)V

    goto :goto_end

    :cond_cp
    invoke-static {v1}, Lcom/ev6/cpwl/Bridge;->writeCp([B)V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    goto :goto_end

    :catch
    move-exception v0

    const-string v1, "EV6CPWL"

    const-string v2, "notify"

    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    goto :goto_end
.end method
