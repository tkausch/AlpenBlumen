//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.


import SwiftUI

@main
struct AlpenBlumenApp: App {
    
    @StateObject private var languageSettings = LanguageSettings()
    
    var body: some Scene {
        WindowGroup {
            // FlowerListView()
            ContentView()
                .environmentObject(languageSettings)
        }
    }
}
