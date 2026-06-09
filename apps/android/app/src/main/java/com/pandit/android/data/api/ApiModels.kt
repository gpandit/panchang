// Models mirroring the gateway's OpenAPI contract.
// Do NOT compute anything here — all Panchang data comes from the API.
package com.pandit.android.data.api

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

// ─── Envelopes ────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class ApiResponse<T>(val data: T)

@JsonClass(generateAdapter = true)
data class PaginatedMeta(
    val total: Int,
    val page: Int,
    @Json(name = "page_size") val pageSize: Int,
    @Json(name = "has_next") val hasNext: Boolean,
)

@JsonClass(generateAdapter = true)
data class PaginatedResponse<T>(
    val data: List<T>,
    val meta: PaginatedMeta,
)

// ─── Panchang ─────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class TimeValueDto(
    val iso: String,
    @Json(name = "hour_24") val hour24: String,
    @Json(name = "hour_12") val hour12: String,
    @Json(name = "hour_24_plus") val hour24Plus: String,
)

@JsonClass(generateAdapter = true)
data class AngaSpanDto(
    val index: Int,
    val name: String,
    val start: TimeValueDto?,
    val end: TimeValueDto?,
)

@JsonClass(generateAdapter = true)
data class DayEventsDto(
    val sunrise: TimeValueDto,
    val sunset: TimeValueDto,
    val moonrise: TimeValueDto?,
    val moonset: TimeValueDto?,
)

@JsonClass(generateAdapter = true)
data class CalendricalDto(
    @Json(name = "shaka_samvat") val shakaSamvat: Int,
    @Json(name = "vikram_samvat") val vikramSamvat: Int,
    @Json(name = "gujarati_samvat") val gujaratiSamvat: Int,
    val samvatsara: String,
    val ritu: String,
    val ayana: String,
    @Json(name = "lunar_month") val lunarMonth: String,
    @Json(name = "is_adhika_month") val isAdhikaMonth: Boolean,
    @Json(name = "is_kshaya_month") val isKshayaMonth: Boolean,
    val paksha: String,
    @Json(name = "moon_rashi") val moonRashi: String,
    @Json(name = "sun_rashi") val sunRashi: String,
)

@JsonClass(generateAdapter = true)
data class PeriodDto(
    val name: String,
    val start: TimeValueDto,
    val end: TimeValueDto,
)

@JsonClass(generateAdapter = true)
data class ChoghadiyaDto(
    val name: String,
    val start: TimeValueDto,
    val end: TimeValueDto,
    @Json(name = "is_day") val isDay: Boolean,
)

@JsonClass(generateAdapter = true)
data class DailyPanchangDto(
    val date: String,
    val lat: Double,
    val lon: Double,
    val tz: String,
    val ayanamsa: String,
    @Json(name = "month_scheme") val monthScheme: String,
    @Json(name = "sun_longitude") val sunLongitude: Double,
    @Json(name = "moon_longitude") val moonLongitude: Double,
    @Json(name = "ayanamsa_value") val ayanamsaValue: Double,
    val tithi: List<AngaSpanDto>,
    val nakshatra: List<AngaSpanDto>,
    val yoga: List<AngaSpanDto>,
    val karana: List<AngaSpanDto>,
    val vara: AngaSpanDto,
    @Json(name = "day_events") val dayEvents: DayEventsDto,
    val muhurat: List<PeriodDto>,
    val choghadiya: List<ChoghadiyaDto>,
    val hora: List<PeriodDto>,
    val calendrical: CalendricalDto,
    val cached: Boolean,
)

@JsonClass(generateAdapter = true)
data class MonthCalendarDto(
    val year: Int,
    val month: Int,
    val days: List<DailyPanchangDto>,
)

// ─── Today / DailyPanchangView ────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class MuhuratWindowDto(
    val name: String,
    val start: TimeValueDto,
    val end: TimeValueDto,
    @Json(name = "is_auspicious") val isAuspicious: Boolean,
)

@JsonClass(generateAdapter = true)
data class FestivalDto(
    val id: String,
    val name: String,
    val date: String,
    val description: String?,
    val tags: List<String>,
    val region: String?,
    val locale: String?,
)

@JsonClass(generateAdapter = true)
data class AdvisoryDto(
    @Json(name = "good_for") val goodFor: List<String>,
    val avoid: List<String>,
)

@JsonClass(generateAdapter = true)
data class DailyHighlightDto(
    val label: String,
    val value: String,
)

@JsonClass(generateAdapter = true)
data class DharmaCardDto(
    val text: String,
    val source: String?,
)

@JsonClass(generateAdapter = true)
data class PanchangElementDto(
    val key: String,
    val label: String,
    val value: String,
    @Json(name = "start_time") val startTime: TimeValueDto?,
    @Json(name = "end_time") val endTime: TimeValueDto?,
    @Json(name = "explanation_key") val explanationKey: String?,
)

@JsonClass(generateAdapter = true)
data class DailyPanchangViewDto(
    val date: String,
    val location: String,
    val tithi: PanchangElementDto,
    val nakshatra: PanchangElementDto,
    val yoga: PanchangElementDto,
    val karana: PanchangElementDto,
    val vara: PanchangElementDto,
    val sunrise: TimeValueDto,
    val sunset: TimeValueDto,
    val moonrise: TimeValueDto?,
    val moonset: TimeValueDto?,
    val muhurats: List<MuhuratWindowDto>,
    val festivals: List<FestivalDto>,
    val advisory: AdvisoryDto,
    val highlights: List<DailyHighlightDto>,
    @Json(name = "dharma_card") val dharmaCard: DharmaCardDto?,
)

// ─── Festivals ─────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class FestivalDetailDto(
    val id: String,
    val name: String,
    val date: String,
    val description: String?,
    val tags: List<String>,
    val region: String?,
    val locale: String?,
    val body: String?,
    val puja: String?,
    val katha: String?,
)

// ─── Notes ────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class NoteDto(
    val id: String,
    val date: String,
    val body: String,
    val tags: List<String>,
    @Json(name = "created_at") val createdAt: String,
    @Json(name = "updated_at") val updatedAt: String,
)

@JsonClass(generateAdapter = true)
data class NoteInputDto(
    val date: String,
    val body: String,
    val tags: List<String>,
)

// ─── Reminders ────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class ReminderDto(
    val id: String,
    val title: String,
    @Json(name = "trigger_type") val triggerType: String,
    @Json(name = "trigger_value") val triggerValue: String,
    @Json(name = "advance_minutes") val advanceMinutes: Int,
    @Json(name = "next_fire_at") val nextFireAt: String?,
    @Json(name = "is_active") val isActive: Boolean,
)

@JsonClass(generateAdapter = true)
data class ReminderInputDto(
    val title: String,
    @Json(name = "trigger_type") val triggerType: String,
    @Json(name = "trigger_value") val triggerValue: String,
    @Json(name = "advance_minutes") val advanceMinutes: Int,
)

// ─── Profile ──────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class LocationDto(
    val id: String,
    val name: String,
    val lat: Double,
    val lon: Double,
    val tz: String,
    @Json(name = "is_default") val isDefault: Boolean,
)

@JsonClass(generateAdapter = true)
data class LocationInputDto(
    val name: String,
    val lat: Double,
    val lon: Double,
    val tz: String,
    @Json(name = "is_default") val isDefault: Boolean,
)

@JsonClass(generateAdapter = true)
data class ProfileDto(
    @Json(name = "user_id") val userId: String,
    val email: String?,
    @Json(name = "display_name") val displayName: String?,
    @Json(name = "default_ayanamsa") val defaultAyanamsa: String,
    @Json(name = "default_month_scheme") val defaultMonthScheme: String,
    val locations: List<LocationDto>,
)

@JsonClass(generateAdapter = true)
data class ProfileUpdateDto(
    @Json(name = "display_name") val displayName: String?,
    @Json(name = "default_ayanamsa") val defaultAyanamsa: String?,
    @Json(name = "default_month_scheme") val defaultMonthScheme: String?,
)

// ─── Auth ─────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class TokenResponseDto(
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "refresh_token") val refreshToken: String?,
    @Json(name = "expires_in") val expiresIn: Int,
)

@JsonClass(generateAdapter = true)
data class GoogleAuthDto(
    @Json(name = "id_token") val idToken: String,
)

@JsonClass(generateAdapter = true)
data class EmailAuthDto(
    val email: String,
    val password: String,
)

@JsonClass(generateAdapter = true)
data class FcmTokenDto(
    @Json(name = "fcm_token") val fcmToken: String,
    val platform: String = "android",
)
