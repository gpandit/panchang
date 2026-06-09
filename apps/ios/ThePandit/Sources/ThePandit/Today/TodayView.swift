// TODO(design): all visual values (colours, spacing, fonts) sourced from DesignTokens — no aesthetic decisions made here.
import SwiftUI
import SwiftData

struct TodayView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.designTokens) private var tokens
    @Bindable var viewModel: TodayViewModel

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading && viewModel.panchang == nil {
                    ProgressView("Loading Panchang…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .accessibilityLabel("Loading today's Panchang")
                } else if let p = viewModel.panchang {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 0) {
                            headerSection(p)
                            timeModeToggle
                            calendricalSection(p.calendrical)
                            panchangAngasSection(p)
                            sunMoonSection(p.dayEvents)
                            muhuratSection(p.muhurat)
                            choghadiyaSection(p.choghadiya)
                            dharmaCard
                        }
                    }
                    .refreshable { await viewModel.load(context: context) }
                } else if let err = viewModel.error {
                    ContentUnavailableView(err, systemImage: "wifi.slash")
                }
            }
            .navigationTitle("Today")
            .toolbar { toolbarContent }
        }
        .task { await viewModel.load(context: context) }
        .sheet(item: $viewModel.showExplanation) { anga in
            AngaExplanationSheet(anga: anga)
        }
        .sheet(item: $viewModel.showMuhuratExplanation) { period in
            PeriodExplanationSheet(period: period)
        }
    }

    // MARK: - Header

    @ViewBuilder
    private func headerSection(_ p: DailyPanchang) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(p.date)
                .font(.caption)
                .foregroundStyle(.secondary)
                .accessibilityLabel("Date: \(p.date)")

            Text(p.calendrical.lunarMonth + " · " + p.calendrical.paksha)
                .font(.headline)
                .accessibilityLabel("Lunar month: \(p.calendrical.lunarMonth), Paksha: \(p.calendrical.paksha)")

            Text(p.calendrical.samvatsara)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding()
        .accessibilityElement(children: .combine)
    }

    // MARK: - Time mode toggle

    private var timeModeToggle: some View {
        Picker("Time display", selection: $viewModel.timeMode) {
            ForEach(TimeDisplayMode.allCases) { mode in
                Text(mode.label).tag(mode)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal)
        .padding(.bottom, 8)
        .accessibilityLabel("Time display format")
    }

    // MARK: - Calendrical details

    @ViewBuilder
    private func calendricalSection(_ c: Calendrical) -> some View {
        SectionCard(title: "Calendrical") {
            DetailRow(label: "Vikram Samvat", value: "\(c.vikramSamvat)")
            DetailRow(label: "Shaka Samvat", value: "\(c.shakaSamvat)")
            DetailRow(label: "Ritu", value: c.ritu)
            DetailRow(label: "Ayana", value: c.ayana)
            DetailRow(label: "Sun Rashi", value: c.sunRashi)
            DetailRow(label: "Moon Rashi", value: c.moonRashi)
            if c.isAdhikaMonth {
                Text("Adhika Maas").font(.caption).foregroundStyle(.orange)
                    .accessibilityLabel("Adhika Maas — intercalary month")
            }
            if c.isKshayaMonth {
                Text("Kshaya Maas").font(.caption).foregroundStyle(.red)
                    .accessibilityLabel("Kshaya Maas")
            }
        }
    }

    // MARK: - Pancha Angas

    @ViewBuilder
    private func panchangAngasSection(_ p: DailyPanchang) -> some View {
        SectionCard(title: "Pancha Anga") {
            AngaRow(label: "Vara (Day)", angas: [p.vara], timeMode: viewModel.timeMode) {
                viewModel.showExplanation = p.vara
            }
            AngaRow(label: "Tithi", angas: p.tithi, timeMode: viewModel.timeMode) {
                viewModel.showExplanation = p.tithi.first
            }
            AngaRow(label: "Nakshatra", angas: p.nakshatra, timeMode: viewModel.timeMode) {
                viewModel.showExplanation = p.nakshatra.first
            }
            AngaRow(label: "Yoga", angas: p.yoga, timeMode: viewModel.timeMode) {
                viewModel.showExplanation = p.yoga.first
            }
            AngaRow(label: "Karana", angas: p.karana, timeMode: viewModel.timeMode) {
                viewModel.showExplanation = p.karana.first
            }
        }
    }

    // MARK: - Sun & Moon

    @ViewBuilder
    private func sunMoonSection(_ events: DayEvents) -> some View {
        SectionCard(title: "Sun & Moon") {
            DetailRow(label: "Sunrise", value: viewModel.formatted(events.sunrise))
            DetailRow(label: "Sunset", value: viewModel.formatted(events.sunset))
            if let moonrise = events.moonrise {
                DetailRow(label: "Moonrise", value: viewModel.formatted(moonrise))
            }
            if let moonset = events.moonset {
                DetailRow(label: "Moonset", value: viewModel.formatted(moonset))
            }
        }
    }

    // MARK: - Muhurat

    @ViewBuilder
    private func muhuratSection(_ muhurats: [Period]) -> some View {
        SectionCard(title: "Auspicious Muhurats") {
            if muhurats.isEmpty {
                Text("No muhurats today").font(.footnote).foregroundStyle(.secondary)
            } else {
                ForEach(muhurats) { m in
                    Button {
                        viewModel.showMuhuratExplanation = m
                    } label: {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(m.name).font(.subheadline)
                                Text("\(viewModel.formatted(m.start)) – \(viewModel.formatted(m.end))")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "info.circle").foregroundStyle(.secondary)
                        }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(m.name): \(viewModel.formatted(m.start)) to \(viewModel.formatted(m.end))")
                    .accessibilityHint("Tap for explanation")
                }
            }
        }
    }

    // MARK: - Choghadiya

    @ViewBuilder
    private func choghadiyaSection(_ items: [Choghadiya]) -> some View {
        SectionCard(title: "Choghadiya") {
            let day = items.filter(\.isDay)
            let night = items.filter { !$0.isDay }
            if !day.isEmpty {
                Text("Day").font(.caption).foregroundStyle(.secondary)
                ForEach(day) { c in
                    DetailRow(label: c.name,
                              value: "\(viewModel.formatted(c.start)) – \(viewModel.formatted(c.end))")
                }
            }
            if !night.isEmpty {
                Text("Night").font(.caption).foregroundStyle(.secondary)
                ForEach(night) { c in
                    DetailRow(label: c.name,
                              value: "\(viewModel.formatted(c.start)) – \(viewModel.formatted(c.end))")
                }
            }
        }
    }

    // MARK: - Dharma Card

    private var dharmaCard: some View {
        // TODO(content): wire to CMS daily dharma endpoint
        SectionCard(title: "Daily Dharma") {
            Text("// TODO(content): daily dharma from CMS")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityLabel("Daily dharma quote — coming soon")
        }
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .navigationBarTrailing) {
            HStack {
                Button {
                    viewModel.isBookmarked.toggle()
                    // TODO(persistence): persist bookmark state
                } label: {
                    Image(systemName: viewModel.isBookmarked ? "bookmark.fill" : "bookmark")
                }
                .accessibilityLabel(viewModel.isBookmarked ? "Remove bookmark" : "Bookmark today")

                ShareLink(item: viewModel.shareText) {
                    Image(systemName: "square.and.arrow.up")
                }
                .accessibilityLabel("Share today's Panchang")
            }
        }
    }
}

// MARK: - Sub-views

private struct SectionCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            content()
        }
        .padding()
        // TODO(design): card background/border from DesignTokens
        .background(.background.secondary)
        .clipShape(RoundedRectangle(cornerRadius: 12)) // TODO(design): radius from tokens
        .padding(.horizontal)
        .padding(.vertical, 4)
    }
}

private struct DetailRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label).font(.subheadline).foregroundStyle(.secondary)
            Spacer()
            Text(value).font(.subheadline)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(label): \(value)")
    }
}

private struct AngaRow: View {
    let label: String
    let angas: [AngaSpan]
    let timeMode: TimeDisplayMode
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 2) {
                Text(label).font(.caption).foregroundStyle(.secondary)
                ForEach(angas) { anga in
                    HStack {
                        Text(anga.name).font(.subheadline)
                        Spacer()
                        if let end = anga.end {
                            Text("until \(formatted(end))").font(.caption).foregroundStyle(.secondary)
                        }
                        Image(systemName: "chevron.right").font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(label): \(angas.map(\.name).joined(separator: ", "))")
        .accessibilityHint("Tap for explanation")
    }

    private func formatted(_ tv: TimeValue) -> String {
        switch timeMode {
        case .hour12: return tv.hour12
        case .hour24: return tv.hour24
        case .hour24plus: return tv.hour24Plus
        }
    }
}

// MARK: - Explanation sheets

private struct AngaExplanationSheet: View {
    let anga: AngaSpan

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(anga.name).font(.title2).bold()
                    // TODO(content): fetch explanation from CMS by anga name
                    Text("Explanation for \(anga.name) will be loaded from the CMS.")
                        .foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle(anga.name)
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }
}

private struct PeriodExplanationSheet: View {
    let period: Period

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(period.name).font(.title2).bold()
                    // TODO(content): muhurat explanation from CMS
                    Text("Details about \(period.name) will be loaded from the CMS.")
                        .foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle(period.name)
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }
}
