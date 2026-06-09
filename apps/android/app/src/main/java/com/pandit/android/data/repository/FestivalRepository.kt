package com.pandit.android.data.repository

import com.pandit.android.data.api.ApiService
import com.pandit.android.data.api.FestivalDetailDto
import com.pandit.android.data.api.FestivalDto
import com.pandit.android.data.db.dao.FestivalDao
import com.pandit.android.data.db.entity.FestivalEntity
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class FestivalRepository @Inject constructor(
    private val api: ApiService,
    private val dao: FestivalDao,
    private val moshi: Moshi,
) {
    private val detailAdapter by lazy { moshi.adapter(FestivalDetailDto::class.java) }
    private val tagsAdapter by lazy {
        moshi.adapter<List<String>>(Types.newParameterizedType(List::class.java, String::class.java))
    }

    fun observeAll(): Flow<List<FestivalDto>> =
        dao.observeAll().map { list -> list.map { it.toDto() } }

    fun observeDetail(id: String): Flow<FestivalDetailDto?> =
        dao.observeById(id).map { entity ->
            entity?.detailJson?.let { detailAdapter.fromJson(it) }
        }

    suspend fun fetchFestivals(year: Int? = null): Result<List<FestivalDto>> = runCatching {
        val response = api.getFestivals(year = year)
        val now = System.currentTimeMillis()
        dao.upsertAll(response.data.map { it.toEntity(now) })
        response.data
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun fetchDetail(id: String): Result<FestivalDetailDto> = runCatching {
        val dto = api.getFestivalDetail(id).data
        dao.updateDetail(id, detailAdapter.toJson(dto))
        dto
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    private fun FestivalDto.toEntity(now: Long) = FestivalEntity(
        id = id,
        name = name,
        date = date,
        description = description,
        tagsJson = tagsAdapter.toJson(tags),
        region = region,
        locale = locale,
        detailJson = null,
        cachedAtMs = now,
    )

    private fun FestivalEntity.toDto() = FestivalDto(
        id = id,
        name = name,
        date = date,
        description = description,
        tags = tagsAdapter.fromJson(tagsJson) ?: emptyList(),
        region = region,
        locale = locale,
    )
}
