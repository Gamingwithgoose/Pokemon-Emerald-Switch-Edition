/* Called only at W3's two verified post-write standby completion checks.
 * No save calls are redirected. The original timer is zero at this boundary;
 * UINT32_MAX marks the extra FRLG readiness round, then is restored to zero.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
extern u32 _IsLinkTaskFinished(void);
extern u8 GetMultiplayerId(void);
extern void SetLinkStandbyCallback(void);
extern u8 gWirelessCommType;
extern u8 gLinkPlayers[];
extern u8 *sTradeAnim;
extern const u32 W5_TimerOffset;

u32 W5_PostWriteReady(void)
{
    u32 ready = _IsLinkTaskFinished();
    u32 version;
    volatile u32 *timer;
    if (!ready || !gWirelessCommType)
        return ready;
    version = *(u16 *)(gLinkPlayers + (GetMultiplayerId() ^ 1) * 28) & 255;
    if (version != 4 && version != 5)
        return ready;
    timer = (volatile u32 *)(sTradeAnim + W5_TimerOffset);
    if (*timer == 0)
    {
        *timer = ~0u;
        SetLinkStandbyCallback();
        return 0;
    }
    if (*timer == ~0u)
        *timer = 0;
    return ready;
}
