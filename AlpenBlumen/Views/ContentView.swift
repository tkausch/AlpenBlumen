//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.


import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            FlowerListView(sortMode: .alphabetical)
                .tabItem {
                    Label("Names", systemImage: "leaf.fill")
                }
            FlowerListView(sortMode: .family)
                .tabItem {
                    Label("Families", systemImage: "tree")
                }
        }
    }
}
