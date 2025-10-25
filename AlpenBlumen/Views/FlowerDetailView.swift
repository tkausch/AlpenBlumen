//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.

import SwiftUI


struct FlowerDetailView: View {
    let flower: Flower
    @State private var isShowingFullScreen = false
    
    @EnvironmentObject var languageSettings: LanguageSettings
    
    var body: some View {
        ScrollView() {
            VStack(spacing: 16) {
                
                // Flower Image
                Image(flower.imageName)
                    .resizable()
                    .scaledToFit()
                    .frame(height: 350)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .shadow(color: Color.black.opacity(0.05), radius: 6, x: 0, y: 3)
                    .onTapGesture {
                        isShowingFullScreen = true
                    }
                    .fullScreenCover(isPresented: $isShowingFullScreen) {
                        FullScreenImageView(imageName: flower.imageName, isPresented: $isShowingFullScreen)
                    }
                
                // Name & Latin Name
                VStack(alignment: .leading, spacing: 4) {
                    Text(flower.localizedName(languageSettings.current))
                        .font(.largeTitle)
                        .bold()
                        .foregroundColor(.primaryText)
                    Text(flower.latin)
                        .font(.title3)
                        .foregroundColor(.secondaryText)
                    
                }
                
                // Systematic Info Card
                VStack(alignment: .leading, spacing: 6) {
                    SystematicRow(title: "Family", value: flower.family)
                    SystematicRow(title: "Genus", value: flower.genus)
                    SystematicRow(title: "Species", value: flower.species)
                }
                .padding()
                .background(Color.cardBackground)
                .cornerRadius(12)
                .shadow(color: Color.black.opacity(0.03), radius: 4, x: 0, y: 2)
                
                // Description
                VStack(spacing: 16)  {
                    Text(flower.localizedDescription(languageSettings.current))
                        .foregroundColor(.primaryText)
                        .lineSpacing(4)
                }
                .padding()
                .background(Color.cardBackground)
                .cornerRadius(12)
                .shadow(color: Color.black.opacity(0.03), radius: 4, x: 0, y: 2)
                
            }
            .padding()
            .navigationTitle(flower.localizedName(languageSettings.current))
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}
