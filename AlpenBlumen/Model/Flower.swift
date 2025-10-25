//
// This File belongs to SwiftRestEssentials 
// Copyright © 2025 Thomas Kausch.
// All Rights Reserved.
import SwiftUI


// MARK: - Datenmodelle
struct Flower: Codable, Identifiable {
    
    static var language = Language.de
    
    // MARK: - JSON Deserialization
    static func loadFlowers() -> [Flower] {
        guard let url = Bundle.main.url(forResource: "AlpenBlumen", withExtension: "json") else {
            assertionFailure("Datei AlpenBlumen.json not found!")
            return []
        }

        do {
            let data = try Data(contentsOf: url)
            let flowers = try JSONDecoder().decode([Flower].self, from: data)
            return flowers
        } catch {
            assertionFailure("Error decoding AlpenBlumen.json!")
            return []
        }
    }
    
    
    
    func localizedName(_ lang: Language) -> String {
        switch lang {
         case .fr:
             return french.name
         case .de:
             return german.name
         case .en:
             return english.name
         }
    }
    
    func localizedDescription(_ lang: Language) -> String {
        switch lang {
         case .fr:
             return french.description
         case .de:
             return german.description
         case .en:
             return english.description
         }
    }
    
    var imageName: String {
        return latin
    }
    
    
    
    let id: UUID = UUID()
    let latin: String
    let family: String
    let genus: String
    
    var  species: String {
        return latin
    }
   
    
    let english: LanguageData
    let german: LanguageData
    let french: LanguageData
    
    enum CodingKeys: String, CodingKey {
        case english
        case german
        case french
        case latin
        case family
        case genus
    }
    
}

struct LanguageData: Codable {
    let name: String
    let description: String
    
    enum CodingKeys: String, CodingKey {
        case name
        case description
    }
}


