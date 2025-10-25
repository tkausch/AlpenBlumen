//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.

import SwiftUI

// MARK: - Systematic Row View
struct SystematicRow: View {
    let title: String
    let value: String
    
    var body: some View {
        HStack {
            Text("\(title):")
                .bold()
                .italic()
                .foregroundColor(.accentColor)
            
            Spacer()
            Text(value)
                .foregroundColor(.primaryText)
        }
    }
}
