package com.pandit.android.data.api

import retrofit2.http.*

interface ApiService {

    // ── Today / Daily view ────────────────────────────────────────────────────

    @GET("panchang/today")
    suspend fun getTodayView(
        @Query("lat") lat: Double,
        @Query("lon") lon: Double,
        @Query("tz") tz: String,
        @Query("ayanamsa") ayanamsa: String = "lahiri",
        @Query("month_scheme") monthScheme: String = "amanta",
    ): ApiResponse<DailyPanchangViewDto>

    // ── Panchang day & month ──────────────────────────────────────────────────

    @GET("panchang/day")
    suspend fun getDayPanchang(
        @Query("date") date: String,
        @Query("lat") lat: Double,
        @Query("lon") lon: Double,
        @Query("tz") tz: String,
        @Query("ayanamsa") ayanamsa: String = "lahiri",
        @Query("month_scheme") monthScheme: String = "amanta",
    ): ApiResponse<DailyPanchangDto>

    @GET("panchang/month")
    suspend fun getMonthCalendar(
        @Query("year") year: Int,
        @Query("month") month: Int,
        @Query("lat") lat: Double,
        @Query("lon") lon: Double,
        @Query("tz") tz: String,
        @Query("ayanamsa") ayanamsa: String = "lahiri",
        @Query("month_scheme") monthScheme: String = "amanta",
    ): ApiResponse<MonthCalendarDto>

    // ── Explanation ───────────────────────────────────────────────────────────

    @GET("panchang/explain/{key}")
    suspend fun getExplanation(
        @Path("key") key: String,
        @Query("lang") lang: String = "en",
    ): ApiResponse<Map<String, String>>

    // ── Festivals ─────────────────────────────────────────────────────────────

    @GET("festivals")
    suspend fun getFestivals(
        @Query("year") year: Int? = null,
        @Query("region") region: String? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 50,
    ): PaginatedResponse<FestivalDto>

    @GET("festivals/{id}")
    suspend fun getFestivalDetail(@Path("id") id: String): ApiResponse<FestivalDetailDto>

    // ── Notes ─────────────────────────────────────────────────────────────────

    @GET("notes")
    suspend fun getNotes(
        @Query("date") date: String? = null,
    ): ApiResponse<List<NoteDto>>

    @POST("notes")
    suspend fun createNote(@Body body: NoteInputDto): ApiResponse<NoteDto>

    @PUT("notes/{id}")
    suspend fun updateNote(@Path("id") id: String, @Body body: NoteInputDto): ApiResponse<NoteDto>

    @DELETE("notes/{id}")
    suspend fun deleteNote(@Path("id") id: String)

    // ── Reminders ─────────────────────────────────────────────────────────────

    @GET("reminders")
    suspend fun getReminders(): ApiResponse<List<ReminderDto>>

    @POST("reminders")
    suspend fun createReminder(@Body body: ReminderInputDto): ApiResponse<ReminderDto>

    @DELETE("reminders/{id}")
    suspend fun deleteReminder(@Path("id") id: String)

    // ── Profile & locations ───────────────────────────────────────────────────

    @GET("profile")
    suspend fun getProfile(): ApiResponse<ProfileDto>

    @PATCH("profile")
    suspend fun updateProfile(@Body body: ProfileUpdateDto): ApiResponse<ProfileDto>

    @POST("profile/locations")
    suspend fun addLocation(@Body body: LocationInputDto): ApiResponse<LocationDto>

    @DELETE("profile/locations/{id}")
    suspend fun removeLocation(@Path("id") id: String)

    // ── Push ──────────────────────────────────────────────────────────────────

    @POST("push/register")
    suspend fun registerFcmToken(@Body body: FcmTokenDto)

    // ── Auth ──────────────────────────────────────────────────────────────────

    @POST("auth/google")
    suspend fun signInWithGoogle(@Body body: GoogleAuthDto): ApiResponse<TokenResponseDto>

    @POST("auth/email")
    suspend fun signInWithEmail(@Body body: EmailAuthDto): ApiResponse<TokenResponseDto>

    @POST("auth/guest")
    suspend fun signInAsGuest(): ApiResponse<TokenResponseDto>

    @POST("auth/refresh")
    suspend fun refreshToken(@Body body: Map<String, String>): ApiResponse<TokenResponseDto>

    @POST("auth/signout")
    suspend fun signOut()
}
