//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.
import SwiftUI

struct FlowerListView: View {
    
    let flowers: [Flower] = Flower.loadFlowers()
    
    let sortMode: SortMode
    
    enum SortMode: String, CaseIterable, Identifiable {
        case alphabetical = "Alphabetically"
        case family = "Family"
        var id: String { rawValue }
    }
    
    @EnvironmentObject var languageSettings: LanguageSettings
    
    init(sortMode: SortMode) {
        self.sortMode = sortMode
    }
    
    // Group flowers by their first letter in the current language
    var groupedFlowers: [(key: String, value: [Flower])] {
        
        var grouped : [String : [Flower]] = [:]
        
        switch sortMode {
            
        case .alphabetical:
            grouped = Dictionary(grouping: flowers) { flower in
                String(flower.localizedName(languageSettings.current).prefix(1)).uppercased()
            }
        case .family:
            grouped = Dictionary(grouping: flowers) { flower in
                flower.family   // 👈 use the family as key
            }
        }
         
        return grouped
            .map { (key: $0.key, value: $0.value.sorted {
                $0.localizedName(languageSettings.current) < $1.localizedName(languageSettings.current)
            })}
            .sorted { $0.key < $1.key }
    }
    
    
    var body: some View {
        NavigationStack {
            NavigationStack {
                List {
                    ForEach(groupedFlowers, id: \.key) { section in
                        Section(header: Text(section.key)) {
                            ForEach(section.value) { flower in
                                NavigationLink {
                                    FlowerDetailView(flower: flower)
                                } label: {
                                    HStack {
                                        Image(flower.imageName)
                                            .resizable()
                                            .scaledToFill()
                                            .frame(width: 50, height: 50)
                                            .clipShape(RoundedRectangle(cornerRadius: 8))
                                            .shadow(color: Color.black.opacity(0.05),
                                                    radius: 2, x: 0, y: 1)
                                        
                                        VStack(alignment: .leading) {
                                            Text(flower.localizedName(languageSettings.current))
                                                .font(.headline)
                                                .foregroundColor(.primaryText)
                                            Text(flower.latin)
                                                .font(.subheadline)
                                                .foregroundColor(.secondary)
                                        }
                                    }
                                    .padding(.vertical, 4)
                                    .listRowBackground(Color.cardBackground)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Blumen")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        ForEach([Language.de, .en, .fr], id: \.self) { lang in
                            Button(action: { languageSettings.current = lang }) {
                                Label(lang.toString,
                                      systemImage: languageSettings.current == lang ? "checkmark" : "")
                            }
                        }
                    } label: {
                        Label("Language", systemImage: "globe")
                    }
                }
            }
        }
    }
}
