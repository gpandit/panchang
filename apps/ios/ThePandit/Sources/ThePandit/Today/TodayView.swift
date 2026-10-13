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
                            panchangAngasSection(p)
                            sunMoonSection(p)
                            muhuratSection(p.muhurats)
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
    private func headerSection(_ p: DailyPanchangViewOut) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(p.date)
                .font(.caption)
                .foregroundStyle(.secondary)
                .accessibilityLabel("Date: \(p.date)")

            Text(p.summaryTitle)
                .font(.headline)
                .accessibilityLabel(p.summaryTitle)

            Text(p.panchangHindiDate)
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

    // MARK: - Pancha Angas

    @ViewBuilder
    private func panchangAngasSection(_ p: DailyPanchangViewOut) -> some View {
        SectionCard(title: "Pancha Anga") {
            ForEach(p.elements.filter { $0.group == "core" }) { element in
                Button {
                    viewModel.showExplanation = element
                } label: {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(element.label).font(.caption).foregroundStyle(.secondary)
                            Text(element.value).font(.subheadline)
                            if let secondary = element.secondaryValue {
                                Text(secondary).font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        Image(systemName: "chevron.right").font(.caption2).foregroundStyle(.secondary)
                    }
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - Sun & Moon

    @ViewBuilder
    private func sunMoonSection(_ p: DailyPanchangViewOut) -> some View {
        SectionCard(title: "Sun & Moon") {
            DetailRow(label: "Sunrise", value: viewModel.formatted(p.sunrise))
            DetailRow(label: "Sunset", value: viewModel.formatted(p.sunset))
            if let moonrise = p.moonrise {
                DetailRow(label: "Moonrise", value: moonrise)
            }
            if let moonset = p.moonset {
                DetailRow(label: "Moonset", value: moonset)
            }
        }
    }

    // MARK: - Muhurat

    @ViewBuilder
    private func muhuratSection(_ muhurats: [MuhuratWindowViewOut]) -> some View {
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
                                Text("\(m.startTime) – \(m.endTime)")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "info.circle").foregroundStyle(.secondary)
                        }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(m.name): \(m.startTime) to \(m.endTime)")
                    .accessibilityHint("Tap for explanation")
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
    let anga: PanchangElementViewOut

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(anga.value).font(.title2).bold()
                    // TODO(content): fetch explanation from CMS by anga name
                    Text(anga.explanation ?? "Explanation for \(anga.label) will be loaded from the CMS.")
                        .foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle(anga.label)
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }
}

private struct PeriodExplanationSheet: View {
    let period: MuhuratWindowViewOut

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(period.name).font(.title2).bold()
                    // TODO(content): muhurat explanation from CMS
                    Text(period.description ?? "Details about \(period.name) will be loaded from the CMS.")
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
