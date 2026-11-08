# Leafia CarPlay bridge (Korean EV6): log to logcat and also to a small file in DiPO's own
# data folder, /data/data/com.daudio.app.dipo/leafia-cp.log (kept to about 256 KB: the
# older half moves to leafia-cp.log.1). The head unit's logcat ring holds only about a
# minute (MicomD fills it), so the moment a wireless session starts was always gone by the
# time a kit ran; the kit copies these files into LEAFIA/private/logs/.
# Same signatures as android.util.Log.i / e, so calls swap in place.
.class final Lcom/ev6/cpwl/Flog;
.super Ljava/lang/Object;
.source "Flog.java"


# direct methods
.method static e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    .registers 6

    invoke-static {p0, p1, p2}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    move-result v0

    :try_start
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, " "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-static {p2}, Landroid/util/Log;->getStackTraceString(Ljava/lang/Throwable;)Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    const-string v2, "E"

    invoke-static {v2, v1}, Lcom/ev6/cpwl/Flog;->put(Ljava/lang/String;Ljava/lang/String;)V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    :catch
    return v0
.end method

.method static i(Ljava/lang/String;Ljava/lang/String;)I
    .registers 4

    invoke-static {p0, p1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    move-result v0

    const-string v1, "I"

    invoke-static {v1, p1}, Lcom/ev6/cpwl/Flog;->put(Ljava/lang/String;Ljava/lang/String;)V

    return v0
.end method

# one line: "MM-dd HH:mm:ss.SSS <level> <text>"; never throws
.method private static put(Ljava/lang/String;Ljava/lang/String;)V
    .registers 8

    const-class v0, Lcom/ev6/cpwl/Flog;

    monitor-enter v0

    :try_start
    new-instance v1, Ljava/io/File;

    const-string v2, "/data/data/com.daudio.app.dipo/leafia-cp.log"

    invoke-direct {v1, v2}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v1}, Ljava/io/File;->length()J

    move-result-wide v2

    const-wide/32 v4, 0x40000

    cmp-long v2, v2, v4

    if-lez v2, :cond_write

    new-instance v2, Ljava/io/File;

    const-string v3, "/data/data/com.daudio.app.dipo/leafia-cp.log.1"

    invoke-direct {v2, v3}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2}, Ljava/io/File;->delete()Z

    invoke-virtual {v1, v2}, Ljava/io/File;->renameTo(Ljava/io/File;)Z

    :cond_write
    new-instance v2, Ljava/io/FileWriter;

    const/4 v3, 0x1

    invoke-direct {v2, v1, v3}, Ljava/io/FileWriter;-><init>(Ljava/io/File;Z)V

    new-instance v3, Ljava/text/SimpleDateFormat;

    const-string v4, "MM-dd HH:mm:ss.SSS "

    sget-object v5, Ljava/util/Locale;->US:Ljava/util/Locale;

    invoke-direct {v3, v4, v5}, Ljava/text/SimpleDateFormat;-><init>(Ljava/lang/String;Ljava/util/Locale;)V

    new-instance v4, Ljava/util/Date;

    invoke-direct {v4}, Ljava/util/Date;-><init>()V

    invoke-virtual {v3, v4}, Ljava/text/SimpleDateFormat;->format(Ljava/util/Date;)Ljava/lang/String;

    move-result-object v3

    invoke-virtual {v2, v3}, Ljava/io/Writer;->write(Ljava/lang/String;)V

    invoke-virtual {v2, p0}, Ljava/io/Writer;->write(Ljava/lang/String;)V

    const-string v3, " "

    invoke-virtual {v2, v3}, Ljava/io/Writer;->write(Ljava/lang/String;)V

    invoke-virtual {v2, p1}, Ljava/io/Writer;->write(Ljava/lang/String;)V

    const-string v3, "\n"

    invoke-virtual {v2, v3}, Ljava/io/Writer;->write(Ljava/lang/String;)V

    invoke-virtual {v2}, Ljava/io/Writer;->close()V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch

    :catch
    monitor-exit v0

    return-void
.end method
