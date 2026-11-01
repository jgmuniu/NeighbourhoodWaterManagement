import 'package:flutter_test/flutter_test.dart';
import 'package:neighbourhood_water_management/main.dart';

void main() {
  testWidgets('app starts', (tester) async {
    await tester.pumpWidget(const WaterApp());
    await tester.pump();
    expect(find.text('Neighbourhood Water Management'), findsWidgets);
  });
}
