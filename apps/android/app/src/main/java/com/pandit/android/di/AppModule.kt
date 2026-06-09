package com.pandit.android.di

import android.content.Context
import androidx.room.Room
import com.pandit.android.BuildConfig
import com.pandit.android.data.api.ApiService
import com.pandit.android.data.api.AuthInterceptor
import com.pandit.android.data.db.PanditDatabase
import com.pandit.android.data.db.dao.*
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideMoshi(): Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    @Provides
    @Singleton
    fun provideOkHttp(authInterceptor: AuthInterceptor): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .apply {
                if (BuildConfig.DEBUG) {
                    addInterceptor(
                        HttpLoggingInterceptor().apply {
                            level = HttpLoggingInterceptor.Level.BODY
                        }
                    )
                }
            }
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, moshi: Moshi): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService =
        retrofit.create(ApiService::class.java)

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): PanditDatabase =
        Room.databaseBuilder(context, PanditDatabase::class.java, "pandit.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun providePanchangDao(db: PanditDatabase): PanchangDao = db.panchangDao()
    @Provides fun provideFestivalDao(db: PanditDatabase): FestivalDao = db.festivalDao()
    @Provides fun provideNoteDao(db: PanditDatabase): NoteDao = db.noteDao()
    @Provides fun provideReminderDao(db: PanditDatabase): ReminderDao = db.reminderDao()
    @Provides fun provideBookmarkDao(db: PanditDatabase): BookmarkDao = db.bookmarkDao()
}
