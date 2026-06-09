// HTTP client bound to the gateway's OpenAPI contract.
// All calls go through this — never bypass to a domain service directly.

import Foundation

enum APIError: Error, LocalizedError {
    case unauthorized
    case notFound
    case serverError(Int)
    case networkError(Error)
    case decodingError(Error)
    case offline

    var errorDescription: String? {
        switch self {
        case .unauthorized: return "Please sign in to continue."
        case .notFound: return "Content not found."
        case .serverError(let code): return "Server error (\(code))."
        case .networkError(let e): return "Network error: \(e.localizedDescription)"
        case .decodingError: return "Response format error."
        case .offline: return "You are offline."
        }
    }
}

// MARK: - APIClient

actor APIClient {
    static let shared = APIClient()

    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL = APIConfiguration.baseURL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session

        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        d.dateDecodingStrategy = .iso8601
        self.decoder = d
    }

    // MARK: Panchang

    func dailyPanchang(date: String, lat: Double, lon: Double, tz: String,
                       ayanamsa: String = "lahiri", monthScheme: String = "amanta") async throws -> DailyPanchang {
        var comps = URLComponents(url: baseURL.appendingPathComponent("v1/panchang/daily"), resolvingAgainstBaseURL: false)!
        comps.queryItems = [
            .init(name: "date", value: date),
            .init(name: "lat", value: "\(lat)"),
            .init(name: "lon", value: "\(lon)"),
            .init(name: "tz", value: tz),
            .init(name: "ayanamsa", value: ayanamsa),
            .init(name: "month_scheme", value: monthScheme),
        ]
        let response: APIResponse<DailyPanchang> = try await get(url: comps.url!)
        return response.data
    }

    func monthCalendar(year: Int, month: Int, lat: Double, lon: Double, tz: String,
                       ayanamsa: String = "lahiri", monthScheme: String = "amanta") async throws -> MonthCalendar {
        var comps = URLComponents(url: baseURL.appendingPathComponent("v1/panchang/month"), resolvingAgainstBaseURL: false)!
        comps.queryItems = [
            .init(name: "year", value: "\(year)"),
            .init(name: "month", value: "\(month)"),
            .init(name: "lat", value: "\(lat)"),
            .init(name: "lon", value: "\(lon)"),
            .init(name: "tz", value: tz),
            .init(name: "ayanamsa", value: ayanamsa),
            .init(name: "month_scheme", value: monthScheme),
        ]
        let response: APIResponse<MonthCalendar> = try await get(url: comps.url!)
        return response.data
    }

    // MARK: Festivals

    func listFestivals(year: Int, month: Int? = nil, region: String? = nil, locale: String? = nil,
                       page: Int = 1, pageSize: Int = 20) async throws -> PaginatedResponse<Festival> {
        var comps = URLComponents(url: baseURL.appendingPathComponent("v1/festivals"), resolvingAgainstBaseURL: false)!
        var items: [URLQueryItem] = [.init(name: "year", value: "\(year)"), .init(name: "page", value: "\(page)"), .init(name: "page_size", value: "\(pageSize)")]
        if let month { items.append(.init(name: "month", value: "\(month)")) }
        if let region { items.append(.init(name: "region", value: region)) }
        if let locale { items.append(.init(name: "locale", value: locale)) }
        comps.queryItems = items
        return try await get(url: comps.url!)
    }

    func festivalDetail(id: String) async throws -> FestivalDetail {
        let url = baseURL.appendingPathComponent("v1/festivals/\(id)")
        let response: APIResponse<FestivalDetail> = try await get(url: url)
        return response.data
    }

    // MARK: Notes

    func listNotes() async throws -> [Note] {
        let url = baseURL.appendingPathComponent("v1/notes")
        let response: APIResponse<[Note]> = try await get(url: url)
        return response.data
    }

    func createNote(_ input: NoteInput) async throws -> Note {
        let url = baseURL.appendingPathComponent("v1/notes")
        let response: APIResponse<Note> = try await post(url: url, body: input)
        return response.data
    }

    func updateNote(id: String, input: NoteInput) async throws -> Note {
        let url = baseURL.appendingPathComponent("v1/notes/\(id)")
        let response: APIResponse<Note> = try await put(url: url, body: input)
        return response.data
    }

    func deleteNote(id: String) async throws {
        let url = baseURL.appendingPathComponent("v1/notes/\(id)")
        try await delete(url: url)
    }

    // MARK: Reminders

    func listReminders() async throws -> [Reminder] {
        let url = baseURL.appendingPathComponent("v1/reminders")
        let response: APIResponse<[Reminder]> = try await get(url: url)
        return response.data
    }

    func createReminder(_ input: ReminderInput) async throws -> Reminder {
        let url = baseURL.appendingPathComponent("v1/reminders")
        let response: APIResponse<Reminder> = try await post(url: url, body: input)
        return response.data
    }

    func deleteReminder(id: String) async throws {
        let url = baseURL.appendingPathComponent("v1/reminders/\(id)")
        try await delete(url: url)
    }

    // MARK: Profile

    func getProfile() async throws -> UserProfile {
        let url = baseURL.appendingPathComponent("v1/profile")
        let response: APIResponse<UserProfile> = try await get(url: url)
        return response.data
    }

    func registerPushToken(_ token: String) async throws {
        let url = baseURL.appendingPathComponent("v1/profile/push-token")
        struct Body: Encodable { let token: String; let platform: String }
        let _: APIResponse<EmptyResponse> = try await post(url: url, body: Body(token: token, platform: "apns"))
    }

    // MARK: - HTTP primitives

    private func get<T: Decodable>(url: URL) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        return try await perform(request)
    }

    private func post<Body: Encodable, T: Decodable>(url: URL, body: Body) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await perform(request)
    }

    private func put<Body: Encodable, T: Decodable>(url: URL, body: Body) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await perform(request)
    }

    private func delete(url: URL) async throws {
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        let _: EmptyResponse = try await performRaw(request)
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        var req = try await authorized(request)
        do {
            let (data, response) = try await session.data(for: req)
            guard let http = response as? HTTPURLResponse else { throw APIError.networkError(URLError(.badServerResponse)) }
            switch http.statusCode {
            case 200...299:
                do { return try decoder.decode(T.self, from: data) } catch { throw APIError.decodingError(error) }
            case 401: throw APIError.unauthorized
            case 404: throw APIError.notFound
            default: throw APIError.serverError(http.statusCode)
            }
        } catch let e as APIError { throw e }
          catch { throw APIError.networkError(error) }
    }

    private func performRaw<T: Decodable>(_ request: URLRequest) async throws -> T {
        return try await perform(request)
    }

    private func authorized(_ request: URLRequest) async throws -> URLRequest {
        var req = request
        if let token = await AuthTokenManager.shared.accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return req
    }
}

private struct EmptyResponse: Decodable {}
