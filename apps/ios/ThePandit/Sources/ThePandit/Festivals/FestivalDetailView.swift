// TODO(design): all visual styling via DesignTokens.
import SwiftUI

struct FestivalDetailView: View {
    let festival: FestivalDetail

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(festival.date)
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if !festival.tags.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack {
                                ForEach(festival.tags, id: \.self) { tag in
                                    Text(tag)
                                        .font(.caption2)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.secondary.opacity(0.15)) // TODO(design)
                                        .clipShape(Capsule())
                                }
                            }
                        }
                    }
                }

                if let desc = festival.description {
                    Text(desc)
                        .font(.body)
                }

                if let body = festival.body {
                    Divider()
                    Text(body)
                        .font(.body)
                        .accessibilityLabel("Festival description")
                }

                if let puja = festival.puja {
                    SectionBlock(title: "Puja Vidhi", content: puja)
                }

                if let katha = festival.katha {
                    SectionBlock(title: "Katha", content: katha)
                }
            }
            .padding()
        }
        .navigationTitle(festival.name)
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                ShareLink(item: "\(festival.name) — \(festival.date)\n\(festival.description ?? "")")
                    .accessibilityLabel("Share festival")
            }
        }
    }
}

private struct SectionBlock: View {
    let title: String
    let content: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            Text(content)
                .font(.body)
        }
    }
}
