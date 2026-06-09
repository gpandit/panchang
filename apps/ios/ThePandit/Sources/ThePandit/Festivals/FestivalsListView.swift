// TODO(design): visual styling via DesignTokens only.
import SwiftUI
import SwiftData

struct FestivalsListView: View {
    @Environment(\.modelContext) private var context
    @Bindable var viewModel: FestivalsViewModel

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading && viewModel.festivals.isEmpty {
                    ProgressView("Loading festivals…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .accessibilityLabel("Loading festivals")
                } else if let err = viewModel.error, viewModel.festivals.isEmpty {
                    ContentUnavailableView(err, systemImage: "wifi.slash")
                } else {
                    list
                }
            }
            .navigationTitle("Festivals")
            .searchable(text: $viewModel.searchText, prompt: "Search festivals")
            .refreshable { await viewModel.load(context: context) }
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Picker("Year", selection: $viewModel.selectedYear) {
                        ForEach((viewModel.selectedYear - 2)...(viewModel.selectedYear + 2), id: \.self) { y in
                            Text("\(y)").tag(y)
                        }
                    }
                    .onChange(of: viewModel.selectedYear) { _, _ in
                        Task { await viewModel.load(context: context) }
                    }
                    .accessibilityLabel("Select year")
                }
            }
        }
        .task { await viewModel.load(context: context) }
        .navigationDestination(item: $viewModel.selectedFestival) { festival in
            FestivalDetailView(festival: festival)
        }
    }

    private var list: some View {
        List(viewModel.filtered) { festival in
            Button {
                Task { await viewModel.loadDetail(id: festival.id) }
            } label: {
                FestivalRow(festival: festival)
            }
            .buttonStyle(.plain)
        }
        .listStyle(.insetGrouped)
        .overlay {
            if viewModel.filtered.isEmpty && !viewModel.searchText.isEmpty {
                ContentUnavailableView.search
            }
        }
    }
}

private struct FestivalRow: View {
    let festival: Festival

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(festival.name)
                .font(.headline)
            Text(festival.date)
                .font(.caption)
                .foregroundStyle(.secondary)
            if let desc = festival.description {
                Text(desc)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            if !festival.tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        ForEach(festival.tags, id: \.self) { tag in
                            Text(tag)
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                // TODO(design): tag background/border via tokens
                                .background(Color.secondary.opacity(0.15))
                                .clipShape(Capsule())
                        }
                    }
                }
            }
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(festival.name), \(festival.date)")
    }
}
