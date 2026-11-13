/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Standalone DLC replacement module configuration.
 */

#pragma once

#ifndef SCE_DLC_EMU_VERSION
#define SCE_DLC_EMU_VERSION "0.4.1-ini-io"
#endif

#ifndef SCE_DLC_EMU_LOG
#define SCE_DLC_EMU_LOG 0
#endif

#ifndef SCE_DLC_EMU_LOG_KERNEL_OUT
#define SCE_DLC_EMU_LOG_KERNEL_OUT 1
#endif

#ifndef SCE_DLC_EMU_LOG_PATH
#define SCE_DLC_EMU_LOG_PATH "/data/shadowmount/dlc_emu_PPSA31246.log"
#endif

#ifndef SCE_DLC_EMU_INI_PATH
#define SCE_DLC_EMU_INI_PATH "/app0/dlc_emu.ini"
#endif

// Per-title persistent fallback for PPSA31246 on ShadowMountPlus.
// The /data/shadowmount/PPSA31246 directory is provided by the image mount
// and is not an independent writable configuration directory.
// Override the macro at build time for other games, or set it to "" to disable.
#ifndef SCE_DLC_EMU_INI_FALLBACK_PATH
#define SCE_DLC_EMU_INI_FALLBACK_PATH "/data/shadowmount/dlc_emu_PPSA31246.ini"
#endif

/* The title's own parameter file, which is where userDefinedParam1..4 live. */
#ifndef SCE_DLC_EMU_PARAM_JSON_PATH
#define SCE_DLC_EMU_PARAM_JSON_PATH "/app0/sce_sys/param.json"
#endif

#ifndef SCE_DLC_EMU_CONTENTIDS_MAX
#define SCE_DLC_EMU_CONTENTIDS_MAX 1024
#endif

#ifndef SCE_DLC_EMU_MOUNT_PREFIX
#define SCE_DLC_EMU_MOUNT_PREFIX "/app0/addcont"
#endif

