//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.
import SwiftUI

enum Language: String, CaseIterable {
    case de, en, fr
    
    var toString: String {
           switch self {
           case .de: return "Deutsch"
           case .en: return "English"
           case .fr: return "Français"
           }
       }
    
}

class LanguageSettings: ObservableObject {
    @Published var current: Language = .de
}
